from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.dependencies import require_admin
from app.database import Base, get_db
from app.main import app
from app.models.ingestion import IngestionJob
from app.models.rag_logging import RagQueryLog
from app.models.textbook import ContentSource, RagChunk
from app.services import rag_evaluation, rag_operations, rag_runtime
from app.services import homework_service
from app.services.chat_service import ask_question
from app.services.rag import RetrievedChunk, cached_retrieved_chunk_allowed, retrieve_context


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture()
def async_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def initialize():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    factory = run_async(initialize())
    yield factory
    run_async(engine.dispose())


@pytest.fixture()
def sync_db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _reviewed_metadata() -> dict:
    return {
        "version": "2026-06-reviewed-v1",
        "status": "reviewed",
        "ready_for_embedding": True,
        "embedding_contract": {
            "required_chunk_metadata": [
                "lesson_id",
                "unit_id",
                "source_type",
                "printed_page_start",
                "printed_page_end",
                "quality_status",
                "reviewed_metadata_version",
            ],
            "allowed_source_types": ["textbook", "solution_book"],
            "blocked_quality_statuses": ["blocked"],
        },
    }


def _chunk(source_id: int, index: int, *, quality: str = "ready", stale: bool = False, complete: bool = False):
    return RagChunk(
        source_id=source_id,
        source_type="textbook",
        chunk_index=index,
        page_number=108 + index,
        content=f"محتوى كيميائي {index}",
        content_type="concept",
        extraction_method="reviewed_jsonl",
        embedding=[0.0] * 768 if complete else None,
        embedding_status="completed" if complete else "pending",
        embedding_model="gemini-embedding-001" if complete else None,
        metadata_json={
            "source_type": "textbook",
            "unit_id": "unit_04",
            "lesson_id": "unit_04_lesson_01",
            "printed_page_start": 108 + index,
            "printed_page_end": 108 + index,
            "quality_status": quality,
            "reviewed_metadata_version": "2026-06-reviewed-v1",
            "stale": stale,
        },
    )


def test_gold_dataset_has_explicit_page_number_contract() -> None:
    cases = rag_evaluation.load_eval_cases("data/eval/rag_gold_questions.json")
    assert len(cases) >= 30
    assert all("expected_printed_pages" in case for case in cases)
    assert all("expected_pdf_pages" in case for case in cases)
    assert all(case["expected_unit_ids"] and case["expected_lesson_ids"] for case in cases)
    assert any("unit_06" in case["expected_unit_ids"] for case in cases)
    coverage = rag_evaluation.build_dataset_coverage(cases)
    assert coverage["reviewed_ready_lesson_count"] == 9
    assert coverage["covered_ready_lesson_count"] == 9
    assert coverage["missing_ready_lesson_ids"] == []
    assert coverage["source_type_case_counts"]["textbook"] >= 1
    assert coverage["source_type_case_counts"]["solution_book"] >= 1


def test_legacy_expected_pages_requires_declared_number_type(tmp_path: Path) -> None:
    dataset = tmp_path / "bad.json"
    dataset.write_text(
        json.dumps({"cases": [{"id": "bad", "query": "سؤال", "expected_pages": [1]}]}),
        encoding="utf-8",
    )
    with pytest.raises(rag_evaluation.EvaluationDatasetError, match=rag_evaluation.EVALUATION_DATASET_INVALID):
        rag_evaluation.load_eval_cases(dataset)


def test_live_evaluation_requires_environment_and_explicit_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RUN_RAG_INTEGRATION", raising=False)
    assert rag_evaluation.live_evaluation_authorized(confirmed=True) is False
    monkeypatch.setenv("RUN_RAG_INTEGRATION", "1")
    assert rag_evaluation.live_evaluation_authorized(confirmed=False) is False
    assert rag_evaluation.live_evaluation_authorized(confirmed=True) is True


def test_evaluation_preflight_excludes_blocked_and_stale_and_requires_complete_vectors(
    async_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rag_evaluation, "load_reviewed_curriculum_metadata", lambda **_kwargs: _reviewed_metadata())
    monkeypatch.setattr(settings, "rag_active_reviewed_metadata_version", "2026-06-reviewed-v1")

    async def scenario():
        async with async_factory() as db:
            source = ContentSource(source_type="textbook", title="Book", status="completed")
            db.add(source)
            await db.flush()
            db.add_all(
                [
                    _chunk(source.id, 0, complete=True),
                    _chunk(source.id, 1, quality="needs_review", complete=False),
                    _chunk(source.id, 2, quality="blocked", complete=False),
                    _chunk(source.id, 3, stale=True, complete=False),
                ]
            )
            await db.commit()
            result = await rag_evaluation.build_evaluation_preconditions(db)
            assert result["counts"]["eligible_chunks"] == 2
            assert result["counts"]["completed_embeddings"] == 1
            assert result["counts"]["blocked_chunks_excluded"] == 1
            assert result["counts"]["stale_chunks_excluded"] == 1
            assert rag_evaluation.EMBEDDING_INDEX_INCOMPLETE in result["blocking_issues"]

    run_async(scenario())


def test_evaluation_preflight_uses_stable_dimension_and_metadata_readiness_codes(
    async_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rag_active_reviewed_metadata_version", "2026-06-reviewed-v1")

    async def metadata_not_ready():
        async with async_factory() as db:
            monkeypatch.setattr(
                rag_evaluation,
                "load_reviewed_curriculum_metadata",
                lambda **_kwargs: (_ for _ in ()).throw(
                    rag_evaluation.ReviewedCurriculumMetadataError(
                        "REVIEWED_CURRICULUM_METADATA_NOT_READY",
                        "not ready",
                    )
                ),
            )
            result = await rag_evaluation.build_evaluation_preconditions(db)
            assert rag_evaluation.REVIEWED_METADATA_NOT_READY in result["blocking_issues"]

    run_async(metadata_not_ready())

    async def wrong_dimension():
        async with async_factory() as db:
            monkeypatch.setattr(
                rag_evaluation,
                "load_reviewed_curriculum_metadata",
                lambda **_kwargs: _reviewed_metadata(),
            )
            source = ContentSource(source_type="textbook", title="Book", status="completed")
            db.add(source)
            await db.flush()
            chunk = _chunk(source.id, 0, complete=True)
            db.add(chunk)
            await db.commit()
            monkeypatch.setattr(settings, "embedding_dimension", 10)
            result = await rag_evaluation.build_evaluation_preconditions(db)
            assert rag_evaluation.EMBEDDING_DIMENSION_MISMATCH in result["blocking_issues"]
            assert rag_evaluation.EMBEDDING_MODEL_MISMATCH not in result["blocking_issues"]

    run_async(wrong_dimension())


def test_kill_switch_returns_before_query_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rag_student_retrieval_enabled", False)
    called = False

    async def forbidden_embed(_query: str):
        nonlocal called
        called = True
        raise AssertionError("query embedding must not run")

    monkeypatch.setattr("app.services.rag.embed_query", forbidden_embed)
    assert run_async(retrieve_context(object(), "ما هي الحموض؟")) == []
    assert called is False


def test_kill_switch_returns_safe_chat_answer_without_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rag_student_retrieval_enabled", False)

    async def forbidden_generation(*_args, **_kwargs):
        raise AssertionError("generation must not run while RAG is disabled")

    monkeypatch.setattr("app.services.chat_service._answer_with_rag_fallback", forbidden_generation)
    result = run_async(ask_question(None, 1, "ما هي الحموض؟", answer_scope="book_only"))
    assert result["confidence"] == 0.0
    assert result["sources"] == []
    assert result["diagnostics"]["reason"] == "RAG_STUDENT_RETRIEVAL_DISABLED"


def test_homework_without_reviewed_context_does_not_call_generator(
    async_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_context(*_args, **_kwargs):
        return []

    async def forbidden_generation(*_args, **_kwargs):
        raise AssertionError("ungrounded Homework generation must not run")

    monkeypatch.setattr(homework_service, "retrieve_context", no_context)
    monkeypatch.setattr(homework_service.ai_service, "get_ai_response", forbidden_generation)

    async def scenario():
        async with async_factory() as db:
            item = await homework_service.solve_text(db, 77, "مسألة خارج المصادر")
            assert item.confidence_score == 0.0
            assert item.source_chunks == []
            assert "لم أجد معلومات كافية" in item.solution

    run_async(scenario())


def test_cache_namespace_changes_with_active_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rag_active_reviewed_metadata_version", "v1")
    first = rag_runtime.rag_cache_namespace()
    monkeypatch.setattr(settings, "rag_active_reviewed_metadata_version", "v2")
    second = rag_runtime.rag_cache_namespace()
    assert first != second


def test_cached_retrieval_requires_current_model_version_and_completed_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rag_active_reviewed_metadata_version", "current-v1")
    monkeypatch.setattr(settings, "gemini_embedding_model", "gemini-embedding-001")
    chunk = RetrievedChunk(
        id=1,
        source_id=1,
        content="محتوى مراجع",
        source="Chemistry.pdf",
        source_type="textbook",
        content_type="concept",
        page_number=108,
        quality_status="ready",
        reviewed_metadata_version="current-v1",
        curriculum_metadata={
            "quality_status": "ready",
            "reviewed_metadata_version": "current-v1",
            "stale": False,
        },
        embedding_status="completed",
        embedding_model="gemini-embedding-001",
    )

    assert cached_retrieved_chunk_allowed(chunk) is True
    chunk.reviewed_metadata_version = "old-v0"
    assert cached_retrieved_chunk_allowed(chunk) is False
    chunk.reviewed_metadata_version = "current-v1"
    chunk.embedding_model = "legacy-model"
    assert cached_retrieved_chunk_allowed(chunk) is False
    chunk.embedding_model = "gemini-embedding-001"
    chunk.embedding_status = "pending"
    assert cached_retrieved_chunk_allowed(chunk) is False
    chunk.embedding_status = "completed"
    chunk.curriculum_metadata = {
        **(chunk.curriculum_metadata or {}),
        "stale": True,
    }
    assert cached_retrieved_chunk_allowed(chunk) is False


def test_production_gate_requires_live_qa_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evaluation_path = tmp_path / "evaluation.json"
    qa_path = tmp_path / "qa.json"
    base = {
        "status": "passed",
        "passed": True,
        "reviewed_metadata_version": "2026-06-reviewed-v1",
        "embedding_model": "gemini-embedding-001",
    }
    evaluation_path.write_text(json.dumps(base), encoding="utf-8")
    qa_path.write_text(json.dumps({**base, "mode": "unit"}), encoding="utf-8")
    monkeypatch.setattr(rag_runtime, "load_reviewed_curriculum_metadata", lambda **_kwargs: _reviewed_metadata())
    monkeypatch.setattr(settings, "rag_evaluation_report_path", str(evaluation_path))
    monkeypatch.setattr(settings, "rag_qa_report_path", str(qa_path))
    monkeypatch.setattr(settings, "rag_active_reviewed_metadata_version", "2026-06-reviewed-v1")
    monkeypatch.setattr(settings, "embedding_provider", "gemini")
    monkeypatch.setattr(settings, "allow_hash_embeddings", False)
    monkeypatch.setattr(settings, "allow_local_embeddings", False)

    assert "RAG_QA_LIVE_REPORT_REQUIRED" in rag_runtime.production_gate_status()["blocking_issues"]
    qa_path.write_text(json.dumps({**base, "mode": "integration"}), encoding="utf-8")
    assert rag_runtime.production_gate_status()["status"] == "ready"


def test_operations_aggregates_existing_logs_without_writes(
    sync_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = RagQueryLog(
        query_text="ما هي الحموض؟",
        route="raw_retrieve",
        top_k=5,
        min_similarity=0.45,
        embedding_model="gemini-embedding-001",
        retrieval_latency_ms=120,
        result_count=2,
        low_confidence=False,
        metadata_json={
            "source_type_counts": {"textbook": 2},
            "quality_status_counts": {"ready": 1, "needs_review": 1},
            "missing_citation_metadata_count": 0,
        },
        created_at=datetime.now(timezone.utc),
    )
    job = IngestionJob(
        job_uid="embed-1",
        status="completed",
        progress=100,
        message="re-embedding completed",
        result_json={"embedding_model": "gemini-embedding-001"},
    )
    sync_db.add_all([log, job])
    sync_db.commit()
    monkeypatch.setattr(rag_operations, "production_gate_status", lambda: {"blocking_issues": []})
    monkeypatch.setattr(rag_operations, "load_json_report", lambda _path: None)
    monkeypatch.setattr(
        rag_operations,
        "build_rag_preflight",
        lambda _db: {
            "status": "ready",
            "can_evaluate": True,
            "chunks": {
                "ready_chunks": 629,
                "needs_review_chunks": 115,
                "blocked_chunks": 0,
                "stale_chunks": 0,
                "pending_embeddings": 0,
                "processing_embeddings": 0,
                "completed_embeddings": 744,
                "failed_embeddings": 0,
            },
            "blocking_issues": [],
            "warnings": [],
        },
    )

    payload = rag_operations.build_rag_operations(sync_db)
    assert payload["query_volume"] == 1
    assert payload["source_type_distribution"] == {"textbook": 2}
    assert payload["quality_status_counts"]["needs_review"] == 1
    assert payload["latest_embedding_job"]["job_id"] == "embed-1"
    assert payload["total_eligible_chunks"] == 744
    assert payload["embedded_eligible_chunks"] == 744
    assert payload["embedding_completion_rate"] == 1.0
    assert payload["ready_chunks"] == 629
    assert payload["needs_review_chunks"] == 115


def test_admin_operations_endpoint_is_read_only(
    sync_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rag_operations, "production_gate_status", lambda: {"blocking_issues": []})
    monkeypatch.setattr(rag_operations, "load_json_report", lambda _path: None)
    monkeypatch.setattr(
        rag_operations,
        "build_rag_preflight",
        lambda _db: {
            "status": "blocked",
            "can_evaluate": False,
            "chunks": {
                "ready_chunks": 0,
                "needs_review_chunks": 0,
                "blocked_chunks": 0,
                "stale_chunks": 0,
                "pending_embeddings": 0,
                "processing_embeddings": 0,
                "completed_embeddings": 0,
                "failed_embeddings": 0,
            },
            "blocking_issues": ["EMBEDDING_INDEX_EMPTY"],
            "warnings": [],
        },
    )

    def override_db():
        yield sync_db

    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin/rag/operations")
        assert response.status_code == 200
        assert response.json()["embedding_model"] == "gemini-embedding-001"
        assert response.json()["preflight_status"] == "blocked"
        assert response.json()["total_eligible_chunks"] == 0
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_db, None)
