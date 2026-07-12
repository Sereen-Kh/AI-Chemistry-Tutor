from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.dependencies import require_admin
from app.database import Base, get_db
from app.main import app
from app.models.textbook import ContentSource, RagChunk
from app.services import rag_preflight
from app.services.reviewed_curriculum_metadata import ReviewedCurriculumMetadataError


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _ready_metadata() -> dict:
    return {
        "status": "reviewed",
        "version": "test-reviewed-v1",
        "ready_for_embedding": True,
        "blocking_issues": [],
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


def _chunk_metadata(quality_status: str) -> dict:
    return {
        "unit_id": "unit_01",
        "lesson_id": "unit_01_lesson_01",
        "source_type": "textbook",
        "printed_page_start": 10,
        "printed_page_end": 10,
        "quality_status": quality_status,
        "reviewed_metadata_version": "test-reviewed-v1",
    }


def _add_chunk(
    db: Session,
    source: ContentSource,
    *,
    index: int,
    quality_status: str,
    embedding_status: str,
    embedding: list[float] | None,
) -> RagChunk:
    chunk = RagChunk(
        source_id=source.id,
        chunk_index=index,
        page_number=10 + index,
        content=f"chunk {index}",
        normalized_content=f"chunk {index}",
        content_type="concept",
        source_type="textbook",
        extraction_method="reviewed_jsonl",
        language="ar",
        embedding_status=embedding_status,
        embedding=embedding,
        metadata_json=_chunk_metadata(quality_status),
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def _mock_production_prerequisites(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rag_preflight,
        "_database_baseline",
        lambda _db: {
            "dialect": "postgresql",
            "reachable": True,
            "pgvector_available": True,
            "pgvector_version": "0.8.2",
            "embedding_dimension": 768,
            "vector_index_present": True,
            "vector_index_name": "rag_chunks_embedding_idx",
            "vector_index_type": "ivfflat",
            "distance_operator": "vector_cosine_ops",
        },
    )
    monkeypatch.setattr(
        rag_preflight,
        "_provider_baseline",
        lambda: {"provider": "gemini", "model": "gemini-embedding-001", "configured": True},
    )
    monkeypatch.setattr(rag_preflight, "_source_baseline", lambda _db: {
        "textbook_found": True,
        "solution_book_found": True,
        "reviewed_textbook_chunks_found": True,
        "reviewed_solution_chunks_found": True,
    })
    metadata = _ready_metadata()
    monkeypatch.setattr(
        rag_preflight,
        "_reviewed_metadata_baseline",
        lambda: ({
            "exists": True,
            "status": "reviewed",
            "version": metadata["version"],
            "ready_for_embedding": True,
            "blocking_issues": [],
        }, metadata),
    )
    monkeypatch.setattr(rag_preflight, "embedding_readiness", lambda: {
        "textbook_chunks_total": 2,
        "solution_chunks_total": 0,
    })


def test_sqlite_preflight_is_blocked_without_crashing(db: Session) -> None:
    payload = rag_preflight.build_rag_preflight(db)

    assert payload["database"]["dialect"] == "sqlite"
    assert payload["database"]["reachable"] is True
    assert payload["database"]["pgvector_available"] is False
    assert payload["status"] == "blocked"
    assert rag_preflight.DATABASE_NOT_POSTGRESQL in payload["blocking_issues"]


def test_production_ready_preflight_excludes_blocked_chunks_from_embedding_gate(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_production_prerequisites(monkeypatch)
    source = ContentSource(source_type="textbook", title="Book", file_path="book.pdf", status="ready")
    db.add(source)
    db.commit()
    db.refresh(source)
    _add_chunk(db, source, index=0, quality_status="ready", embedding_status="completed", embedding=[0.0] * 768)
    _add_chunk(
        db,
        source,
        index=1,
        quality_status="needs_review",
        embedding_status="completed",
        embedding=[0.0] * 768,
    )
    _add_chunk(db, source, index=2, quality_status="blocked", embedding_status="pending", embedding=None)

    payload = rag_preflight.build_rag_preflight(db)

    assert payload["status"] == "ready"
    assert payload["can_evaluate"] is True
    assert payload["chunks"]["blocked_chunks"] == 1
    assert payload["chunks"]["pending_embeddings"] == 0
    assert payload["chunks"]["completed_embeddings"] == 2


def test_preflight_reports_pending_failed_and_wrong_dimension(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_production_prerequisites(monkeypatch)
    source = ContentSource(source_type="textbook", title="Book", file_path="book.pdf", status="ready")
    db.add(source)
    db.commit()
    db.refresh(source)
    _add_chunk(db, source, index=0, quality_status="ready", embedding_status="pending", embedding=None)
    _add_chunk(db, source, index=1, quality_status="ready", embedding_status="failed", embedding=None)
    _add_chunk(
        db,
        source,
        index=2,
        quality_status="ready",
        embedding_status="completed",
        embedding=[0.0] * 768,
    )
    original_chunk_baseline = rag_preflight._chunk_baseline

    def wrong_dimension_baseline(*args, **kwargs):
        result = original_chunk_baseline(*args, **kwargs)
        result["wrong_dimension_embeddings"] = 1
        return result

    monkeypatch.setattr(rag_preflight, "_chunk_baseline", wrong_dimension_baseline)

    payload = rag_preflight.build_rag_preflight(db)

    assert payload["can_embed"] is True
    assert payload["can_evaluate"] is False
    assert payload["chunks"]["pending_embeddings"] == 1
    assert payload["chunks"]["failed_embeddings"] == 1
    assert payload["chunks"]["wrong_dimension_embeddings"] == 1
    assert rag_preflight.WRONG_EMBEDDING_DIMENSION in payload["blocking_issues"]


def test_preflight_reports_vector_status_and_model_inconsistencies(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_production_prerequisites(monkeypatch)
    source = ContentSource(source_type="textbook", title="Book", file_path="book.pdf", status="ready")
    db.add(source)
    db.commit()
    db.refresh(source)
    _add_chunk(db, source, index=0, quality_status="ready", embedding_status="completed", embedding=None)
    mismatch = _add_chunk(
        db,
        source,
        index=1,
        quality_status="ready",
        embedding_status="pending",
        embedding=[0.0] * 768,
    )
    mismatch.embedding_model = "old-embedding-model"
    db.commit()

    payload = rag_preflight.build_rag_preflight(db)

    assert payload["chunks"]["completed_vectors_missing"] == 1
    assert payload["chunks"]["noncompleted_with_embeddings"] == 1
    assert payload["chunks"]["embedding_model_mismatch"] == 1
    assert rag_preflight.COMPLETED_VECTOR_MISSING in payload["blocking_issues"]
    assert rag_preflight.EMBEDDING_MODEL_MISMATCH in payload["blocking_issues"]


def test_preflight_reports_missing_or_not_ready_metadata(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(*_args, **_kwargs):
        raise ReviewedCurriculumMetadataError("REVIEWED_CURRICULUM_METADATA_MISSING")

    monkeypatch.setattr(rag_preflight, "load_reviewed_curriculum_metadata", missing)
    payload = rag_preflight.build_rag_preflight(db)
    assert payload["reviewed_metadata"]["exists"] is False
    assert rag_preflight.REVIEWED_METADATA_MISSING in payload["blocking_issues"]

    metadata = _ready_metadata()
    metadata["ready_for_embedding"] = False
    monkeypatch.setattr(rag_preflight, "load_reviewed_curriculum_metadata", lambda **_kwargs: metadata)
    payload = rag_preflight.build_rag_preflight(db)
    assert payload["reviewed_metadata"]["exists"] is True
    assert payload["reviewed_metadata"]["ready_for_embedding"] is False
    assert rag_preflight.REVIEWED_METADATA_NOT_READY in payload["blocking_issues"]


def test_preflight_reports_missing_gemini_configuration(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_production_prerequisites(monkeypatch)
    monkeypatch.setattr(
        rag_preflight,
        "_provider_baseline",
        lambda: {"provider": "gemini", "model": "gemini-embedding-001", "configured": False},
    )

    payload = rag_preflight.build_rag_preflight(db)

    assert payload["provider"]["configured"] is False
    assert rag_preflight.GEMINI_EMBEDDING_NOT_CONFIGURED in payload["blocking_issues"]


def test_admin_preflight_endpoint_requires_admin_and_never_exposes_secrets(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr("app.core.dependencies.settings.admin_token", "top-secret-admin-token")
    try:
        with TestClient(app) as client:
            unauthorized = client.get("/api/v1/admin/rag/preflight")
            assert unauthorized.status_code in {401, 403}

        app.dependency_overrides[require_admin] = lambda: None
        with TestClient(app) as client:
            response = client.get("/api/v1/admin/rag/preflight")
            assert response.status_code == 200
            assert "top-secret-admin-token" not in response.text
            assert "database_url" not in response.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_admin, None)


def test_preflight_cli_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import run_rag_preflight

    class Context:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    payload = {
        "status": "ready",
        "database": {"dialect": "postgresql", "reachable": True, "pgvector_version": "0.8.2"},
        "reviewed_metadata": {"ready_for_embedding": True},
        "chunks": {"reviewed_chunks_total": 2, "database_chunks_total": 2, "completed_embeddings": 2},
        "can_load_chunks": True,
        "can_embed": False,
        "can_evaluate": True,
        "blocking_issues": [],
        "warnings": [],
    }
    monkeypatch.setattr(run_rag_preflight, "SessionLocal", lambda: Context())
    monkeypatch.setattr(run_rag_preflight, "build_rag_preflight", lambda _db: payload)
    monkeypatch.setattr("sys.argv", ["run_rag_preflight.py"])

    assert run_rag_preflight.main() == 0
