"""Focused tests for RAG hardening configuration and admin surfaces."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database import Base
from app.main import app
from app.models.textbook import ContentSource, RagChunk
from app.services.embeddings import (
    EMBEDDING_DIM,
    GeminiEmbeddingQuotaError,
    embed_document,
    embed_documents_batch,
    embed_query,
)
from app.services.rag_evaluation import _threshold_failures
from app.services.rag_logging import log_rag_retrieval
from app.services.rag_reembed import (
    QUOTA_ERROR_CODE,
    _metadata_with_embedding_model,
    redact_embedding_error,
    reembed_all_chunks,
    reembed_rag_chunks,
)
from app.services.reviewed_curriculum_metadata import (
    NOT_READY_CODE,
    ReviewedCurriculumMetadataError,
)
from app.workers.celery_app import celery_app


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture()
def rag_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def init() -> async_sessionmaker[AsyncSession]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    factory = run_async(init())
    yield factory
    run_async(engine.dispose())


async def _seed_rag_chunks(db: AsyncSession) -> tuple[ContentSource, ContentSource, list[RagChunk]]:
    textbook = ContentSource(source_type="textbook", title="Chemistry textbook", status="completed")
    solutions = ContentSource(source_type="solution_book", title="Chemistry solutions", status="completed")
    db.add_all([textbook, solutions])
    await db.commit()
    await db.refresh(textbook)
    await db.refresh(solutions)
    chunks = [
        RagChunk(
            source_id=textbook.id,
            source_type="textbook",
            chunk_index=0,
            page_number=11,
            content="تعريف الحمض وأيونات الهدروجين H+",
            normalized_content="تعريف الحمض وايونات الهدروجين H+",
            content_type="definition",
        ),
        RagChunk(
            source_id=textbook.id,
            source_type="textbook",
            chunk_index=1,
            page_number=12,
            content="قانون التركيز المولي C = n / V",
            normalized_content="قانون التركيز المولي C = n / V",
            content_type="formula",
        ),
        RagChunk(
            source_id=solutions.id,
            source_type="solution_book",
            chunk_index=0,
            page_number=4,
            content="حل مسألة تركيز HCl",
            normalized_content="حل مسالة تركيز HCl",
            content_type="solution",
        ),
    ]
    db.add_all(chunks)
    await db.commit()
    for chunk in chunks:
        await db.refresh(chunk)
    return textbook, solutions, chunks


def _vector(value: float) -> list[float]:
    return [value] * EMBEDDING_DIM


def test_embedding_dimension_is_768() -> None:
    assert EMBEDDING_DIM == 768
    assert settings.embedding_dimension == 768


def test_hash_embeddings_are_rejected_when_not_explicitly_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "local_hash")
    monkeypatch.setattr(settings, "allow_hash_embeddings", False)

    with pytest.raises(RuntimeError, match="ALLOW_HASH_EMBEDDINGS=false"):
        asyncio.run(embed_query("ما تعريف الحمض؟"))


def test_embedding_dimension_is_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    async def bad_embed(_text: str, _task_type: str) -> list[float]:
        return [0.1] * 3

    monkeypatch.setattr("app.services.embeddings._embed_one", bad_embed)

    with pytest.raises(RuntimeError, match="expected 768"):
        run_async(embed_document("short document"))


def test_logging_failure_does_not_break_retrieval_path(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenSession:
        async def __aenter__(self):
            raise RuntimeError("database unavailable")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(settings, "rag_query_logging_enabled", True)
    monkeypatch.setattr("app.services.rag_logging.AsyncSessionLocal", lambda: BrokenSession())

    result = asyncio.run(
        log_rag_retrieval(
            user_id=1,
            query_text="ما تعريف الحمض؟",
            normalized_query="ما تعريف الحمض",
            route="raw_retrieve",
            source_mode="textbook",
            top_k=5,
            min_similarity=0.45,
            chunks=[
                SimpleNamespace(
                    id=10,
                    source_id=1,
                    source_type="textbook",
                    page_number=11,
                    content_type="definition",
                    similarity_score=0.92,
                )
            ],
        )
    )

    assert result is None


def test_reembedding_service_fails_fast_when_reviewed_metadata_not_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata_path = tmp_path / "reviewed_curriculum_metadata.json"
    metadata_path.write_text(
        json.dumps({"ready_for_embedding": False, "version": "test"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.reviewed_curriculum_metadata.REVIEWED_METADATA_PATH", metadata_path)

    class FakeDb:
        scalar_calls = 0

        async def scalar(self, _stmt):
            self.scalar_calls += 1
            return 7

    fake_db = FakeDb()
    with pytest.raises(ReviewedCurriculumMetadataError) as exc:
        asyncio.run(reembed_rag_chunks(fake_db, dry_run=True, batch_size=10))

    assert exc.value.code == NOT_READY_CODE
    assert fake_db.scalar_calls == 0


def test_reembedding_dry_run_does_not_update_embeddings() -> None:
    class FakeDb:
        async def scalar(self, _stmt):
            return 7

    result = asyncio.run(reembed_all_chunks(FakeDb(), dry_run=True, batch_size=10))
    assert result.status == "completed"
    assert result.dry_run is True
    assert result.updated == 0
    assert result.total_candidates == 7


def test_reembedding_dry_run_does_not_update_database(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(float(index + 1)) for index, _text in enumerate(texts)]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(db, dry_run=True, force=True)
            refreshed = await db.get(RagChunk, chunks[0].id)
            assert refreshed is not None
            assert refreshed.embedding is None
            assert result.total_chunks == 3
            assert result.updated == 0

    run_async(scenario())


def test_reembedding_updates_vectors_and_metadata(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(float(index + 1)) for index, _text in enumerate(texts)]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(db, dry_run=False, force=True, batch_size=2)
            refreshed = await db.get(RagChunk, chunks[0].id)
            assert refreshed is not None
            assert refreshed.embedding == _vector(1.0)
            assert refreshed.embedding_model == settings.gemini_embedding_model
            assert refreshed.embedding_status == "completed"
            assert refreshed.embedding_updated_at is not None
            assert refreshed.embedding_error is None
            assert isinstance(refreshed.metadata_json, dict)
            assert refreshed.metadata_json["quality_status"] == "needs_review"
            assert refreshed.metadata_json["review_status"] == "legacy_unmapped"
            assert str(refreshed.metadata_json["unit_id"]).startswith("unmapped:textbook:")
            assert str(refreshed.metadata_json["lesson_id"]).startswith("unmapped:textbook:")
            assert result.updated == 3
            assert result.failed == 0

    run_async(scenario())


def test_reembedding_downgrades_legacy_ready_chunks_without_lesson_unit_metadata(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(8.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            legacy_ready = chunks[0]
            legacy_ready.metadata_json = {
                "source_type": "textbook",
                "printed_page_start": 11,
                "printed_page_end": 11,
                "quality_status": "ready",
            }
            await db.commit()

            result = await reembed_rag_chunks(db, dry_run=False, force=True, batch_size=2)
            refreshed = await db.get(RagChunk, legacy_ready.id)
            assert refreshed is not None
            assert isinstance(refreshed.metadata_json, dict)
            assert refreshed.metadata_json["quality_status"] == "needs_review"
            assert refreshed.metadata_json["review_status"] == "legacy_unmapped"
            assert str(refreshed.metadata_json["unit_id"]).startswith("unmapped:textbook:")
            assert str(refreshed.metadata_json["lesson_id"]).startswith("unmapped:textbook:")
            assert refreshed.embedding == _vector(8.0)
            assert result.updated == 3

    run_async(scenario())


def test_reembedding_excludes_blocked_chunks_from_readiness_checks(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedded_texts: list[str] = []

    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        embedded_texts.extend(texts)
        return [_vector(6.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            blocked = chunks[0]
            blocked.metadata_json = {
                "lesson_id": "unit_04_lesson_02",
                "unit_id": "unit_04",
                "source_type": "textbook",
                "printed_page_start": 11,
                "printed_page_end": 11,
                "quality_status": "blocked",
                "reviewed_metadata_version": "2026-06-reviewed-v1",
            }
            await db.commit()

            result = await reembed_rag_chunks(db, dry_run=False, force=True, batch_size=3)
            refreshed_blocked = await db.get(RagChunk, blocked.id)
            assert refreshed_blocked is not None
            assert refreshed_blocked.embedding is None
            assert refreshed_blocked.embedding_status == "skipped"
            assert refreshed_blocked.embedding_error == "blocked_quality_status"
            assert result.updated == 2
            assert result.skipped_blocked_count == 1
            assert "تعريف الحمض" not in embedded_texts

    run_async(scenario())


def test_reembedding_skips_current_model_when_force_false(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(9.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            current = chunks[0]
            current.embedding = _vector(2.0)
            current.embedding_model = settings.gemini_embedding_model
            current.embedding_status = "completed"
            await db.commit()

            result = await reembed_rag_chunks(db, dry_run=False, force=False)
            refreshed = await db.get(RagChunk, current.id)
            assert refreshed is not None
            assert refreshed.embedding == _vector(2.0)
            assert result.skipped >= 1
            assert result.updated == 2

    run_async(scenario())


def test_force_true_reembeds_current_model_chunks(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(7.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            chunks[0].embedding = _vector(2.0)
            chunks[0].embedding_model = settings.gemini_embedding_model
            chunks[0].embedding_status = "completed"
            await db.commit()

            result = await reembed_rag_chunks(db, dry_run=False, force=True)
            refreshed = await db.get(RagChunk, chunks[0].id)
            assert refreshed is not None
            assert refreshed.embedding == _vector(7.0)
            assert result.updated == 3

    run_async(scenario())


def test_reembedding_source_filters(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(4.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            textbook, solutions, chunks = await _seed_rag_chunks(db)
            by_type = await reembed_rag_chunks(db, source_type="solution_book", dry_run=False, force=True)
            refreshed_solution = await db.get(RagChunk, chunks[2].id)
            refreshed_textbook = await db.get(RagChunk, chunks[0].id)
            assert refreshed_solution is not None
            assert refreshed_textbook is not None
            assert refreshed_solution.embedding == _vector(4.0)
            assert refreshed_textbook.embedding is None
            assert by_type.updated == 1

            by_source = await reembed_rag_chunks(db, source_id=textbook.id, dry_run=True, force=True)
            assert by_source.total_chunks == 2
            assert by_source.source_id == textbook.id
            assert solutions.id != textbook.id

    run_async(scenario())


def test_failed_chunks_store_embedding_error_and_resume_failed_only(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        raise RuntimeError("batch unavailable")

    async def selective_document(text: str) -> list[float]:
        if "تركيز" in text:
            raise RuntimeError("cannot embed concentration chunk")
        return _vector(5.0)

    async def no_wait(_delay: float) -> None:
        return None

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", failing_batch)
    monkeypatch.setattr("app.services.rag_reembed.embed_document", selective_document)
    monkeypatch.setattr("app.services.rag_reembed.asyncio.sleep", no_wait)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(db, dry_run=False, force=True)
            failed_chunk = await db.get(RagChunk, chunks[1].id)
            assert failed_chunk is not None
            assert failed_chunk.embedding_status == "failed"
            assert "cannot embed" in (failed_chunk.embedding_error or "")
            assert result.failed >= 1
            stale_processing_chunk = await db.get(RagChunk, chunks[2].id)
            assert stale_processing_chunk is not None
            stale_processing_chunk.embedding_status = "processing"
            stale_processing_chunk.embedding = None
            await db.commit()

            resume = await reembed_rag_chunks(db, dry_run=True, resume_failed=True)
            assert resume.total_candidates >= 2

    run_async(scenario())


def test_reembedding_retries_transient_batch_failure_with_backoff(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    delays: list[float] = []

    async def flaky_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary network failure")
        return [_vector(3.0) for _text in texts]

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", flaky_batch)
    monkeypatch.setattr("app.services.rag_reembed.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("app.services.rag_reembed.random.uniform", lambda _start, _end: 0.0)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(db, dry_run=False, force=True, batch_size=3)
            assert result.status == "completed"
            assert result.updated == 3
            assert result.retry_count == 1
            assert result.last_retry_delay_seconds == 2.0
            assert attempts == 2
            assert delays == [2.0]

    run_async(scenario())


def test_reembedding_quota_failure_pauses_without_per_chunk_fanout(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_calls = 0
    document_calls = 0

    def quota_batch(_texts: list[str], _task_type: str) -> list[list[float]]:
        nonlocal batch_calls
        batch_calls += 1
        raise RuntimeError("429 RESOURCE_EXHAUSTED retryDelay: 17s")

    async def document_must_not_run(_text: str) -> list[float]:
        nonlocal document_calls
        document_calls += 1
        return _vector(1.0)

    monkeypatch.setattr(settings, "embedding_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "configured-test-key")
    monkeypatch.setattr(settings, "allow_hash_embeddings", False)
    monkeypatch.setattr("app.services.embeddings._GEMINI_DISABLED_REASON", None)
    monkeypatch.setattr("app.services.embeddings._embed_gemini_batch", quota_batch)
    monkeypatch.setattr("app.services.rag_reembed.embed_document", document_must_not_run)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(db, dry_run=False, force=True, batch_size=3)
            assert result.status == "paused_quota"
            assert result.stopped_reason == QUOTA_ERROR_CODE
            assert result.quota_events == 1
            assert result.retry_after_seconds == 17.0
            assert result.updated == 0
            assert batch_calls == 1
            assert document_calls == 0
            for chunk in chunks:
                refreshed = await db.get(RagChunk, chunk.id)
                assert refreshed is not None
                assert refreshed.embedding is None
                assert refreshed.embedding_status == "pending"
                assert refreshed.embedding_error == QUOTA_ERROR_CODE

    run_async(scenario())


def test_embedding_wrapper_preserves_quota_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def quota_batch(_texts: list[str], _task_type: str) -> list[list[float]]:
        raise RuntimeError("429 RESOURCE_EXHAUSTED retryDelay: 23s")

    def hash_fallback_must_not_run(_text: str, _dim: int = EMBEDDING_DIM) -> list[float]:
        raise AssertionError("hash fallback must not run after Gemini quota exhaustion")

    monkeypatch.setattr(settings, "embedding_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "configured-test-key")
    monkeypatch.setattr(settings, "allow_hash_embeddings", False)
    monkeypatch.setattr("app.services.embeddings._GEMINI_DISABLED_REASON", None)
    monkeypatch.setattr("app.services.embeddings._embed_gemini_batch", quota_batch)
    monkeypatch.setattr("app.services.embeddings._fallback_embedding", hash_fallback_must_not_run)

    with pytest.raises(GeminiEmbeddingQuotaError, match="GEMINI_EMBEDDING_QUOTA_EXCEEDED"):
        run_async(embed_documents_batch(["first", "second"], batch_size=2))


def test_reembedding_progress_callback_runs_after_each_committed_batch(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_events: list[dict] = []

    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(4.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(
                db,
                dry_run=False,
                force=True,
                batch_size=2,
                progress_callback=progress_events.append,
            )
            assert result.updated == 3
            assert result.batches_completed == 2
            assert [event["updated"] for event in progress_events] == [2, 3]
            assert [event["batches_completed"] for event in progress_events] == [1, 2]
            assert progress_events[-1]["last_chunk_id"] == result.last_chunk_id

    run_async(scenario())


def test_reembedding_paces_later_batches(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delays: list[float] = []

    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(4.0) for _text in texts]

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)
    monkeypatch.setattr("app.services.rag_reembed.asyncio.sleep", fake_sleep)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(
                db,
                dry_run=False,
                force=True,
                batch_size=2,
                batch_delay_seconds=21.0,
            )
            assert result.status == "completed"
            assert result.batches_completed == 2
            assert result.batch_delay_seconds == 21.0
            assert delays == [21.0]

    run_async(scenario())


def test_reembedding_resumes_after_checkpoint_and_preserves_completed_vector(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [_vector(7.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            chunks[0].embedding = _vector(2.0)
            chunks[0].embedding_model = settings.gemini_embedding_model
            chunks[0].embedding_status = "completed"
            chunks[1].embedding_status = "processing"
            await db.commit()

            result = await reembed_rag_chunks(
                db,
                dry_run=False,
                force=False,
                resume_failed=True,
                resume_after_chunk_id=chunks[0].id,
                batch_size=2,
            )
            first = await db.get(RagChunk, chunks[0].id)
            second = await db.get(RagChunk, chunks[1].id)
            third = await db.get(RagChunk, chunks[2].id)
            assert first is not None and first.embedding == _vector(2.0)
            assert second is not None and second.embedding == _vector(7.0)
            assert third is not None and third.embedding == _vector(7.0)
            assert result.updated == 2

    run_async(scenario())


def test_reembedding_rejects_wrong_dimension_without_marking_completed(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def wrong_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _text in texts]

    async def wrong_document(_text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", wrong_batch)
    monkeypatch.setattr("app.services.rag_reembed.embed_document", wrong_document)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            result = await reembed_rag_chunks(db, dry_run=False, force=True, batch_size=3)
            assert result.status == "completed_with_errors"
            assert result.failed == 3
            for chunk in chunks:
                refreshed = await db.get(RagChunk, chunk.id)
                assert refreshed is not None
                assert refreshed.embedding is None
                assert refreshed.embedding_status == "failed"

    run_async(scenario())


def test_reembedding_excludes_invalid_source_metadata_without_provider_call(
    rag_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedded_texts: list[str] = []

    async def fake_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
        embedded_texts.extend(texts)
        return [_vector(6.0) for _text in texts]

    monkeypatch.setattr("app.services.rag_reembed.embed_documents_batch", fake_batch)

    async def scenario() -> None:
        async with rag_session_factory() as db:
            _textbook, _solutions, chunks = await _seed_rag_chunks(db)
            invalid = chunks[0]
            invalid.source_type = "unknown"
            invalid.metadata_json = {
                "unit_id": "unit_04",
                "lesson_id": "unit_04_lesson_01",
                "printed_page_start": 11,
                "printed_page_end": 11,
                "quality_status": "ready",
                "reviewed_metadata_version": "2026-06-reviewed-v1",
            }
            await db.commit()

            result = await reembed_rag_chunks(db, dry_run=False, force=True, batch_size=3)
            refreshed = await db.get(RagChunk, invalid.id)
            assert refreshed is not None
            assert refreshed.embedding is None
            assert refreshed.embedding_status == "skipped"
            assert result.updated == 2
            assert "تعريف الحمض" not in embedded_texts

    run_async(scenario())


def test_embedding_errors_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "secret-test-key")
    error = RuntimeError("api_key=secret-test-key provider connection failed")

    redacted = redact_embedding_error(error)

    assert "secret-test-key" not in redacted
    assert "***redacted***" in redacted


def test_reembedding_metadata_records_model() -> None:
    metadata = _metadata_with_embedding_model({"source": "fixture"}, "gemini-embedding-001")
    assert metadata["embedding_model"] == "gemini-embedding-001"
    assert metadata["embedding_dimension"] == 768
    assert metadata["source"] == "fixture"
    assert metadata["embedding_updated_at"]


def test_evaluation_threshold_failures_are_detected() -> None:
    failures = _threshold_failures(
        {
            "top5_expected_page_hit_rate": 0.1,
            "no_result_rate": 0.5,
            "wrong_source_rate": 0.4,
            "low_confidence_rate": 0.6,
            "average_retrieval_latency_ms": 3000,
        }
    )
    assert len(failures) == 5


def test_admin_rag_routes_are_protected() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/admin/rag/query-logs")
    assert response.status_code in {401, 403}


def test_celery_rag_reembed_task_is_registered() -> None:
    assert "reembed_rag_chunks" in celery_app.tasks
