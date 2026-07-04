from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.dependencies import require_admin
from app.database import Base, get_db
from app.main import app
from app.services.reviewed_curriculum_metadata import (
    NOT_READY_CODE,
    ReviewedCurriculumMetadataError,
    load_reviewed_curriculum_metadata,
)
from app.services.reviewed_ingestion_assets import (
    canonical_source_statuses,
    prepare_reviewed_chunks,
)


@pytest.fixture()
def admin_db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def admin_client(admin_db: Session) -> Iterator[TestClient]:
    def override_db():
        yield admin_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_admin] = lambda: None
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_admin, None)


def test_canonical_source_detection_reads_both_pdfs() -> None:
    sources = canonical_source_statuses()

    by_type = {source["source_type"]: source for source in sources}
    assert by_type["textbook"]["exists"] is True
    assert by_type["textbook"]["page_count"] == 96
    assert by_type["textbook"]["sha256"] == "3e94fe8be9d4c750c0253d3b81dc12ddf826ec6c901a2def17427d32cb5f9187"
    assert by_type["solution_book"]["exists"] is True
    assert by_type["solution_book"]["page_count"] == 35
    assert by_type["solution_book"]["sha256"] == "2b8ed4051308d3f52d8fb1c33ffc8da50f539db882624ef318a9b68dedd9b1c0"


def test_prepare_reviewed_chunks_dry_run_prefers_reviewed_outputs() -> None:
    result = prepare_reviewed_chunks(write=False)

    assert result["ready_for_embedding"] is True
    assert result["textbook"]["chunks_total"] == 720
    assert result["textbook"]["missing_metadata_after"] == 0
    assert result["solution_book"]["chunks_total"] == 24
    assert result["solution_book"]["legacy_chunks_used"] is False
    assert result["solution_book"]["bad_endings_count"] == 0
    assert result["solution_book"]["manual_review_count"] == 17
    assert result["counts"]["solution_chunks_ready"] == 7
    assert result["counts"]["solution_chunks_needs_review"] == 17


def test_reviewed_metadata_guard_blocks_false_ready_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata_path = tmp_path / "reviewed_curriculum_metadata.json"
    metadata_path.write_text(
        json.dumps({"ready_for_embedding": False, "version": "test"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.reviewed_curriculum_metadata.REVIEWED_METADATA_PATH", metadata_path)

    with pytest.raises(ReviewedCurriculumMetadataError) as exc:
        load_reviewed_curriculum_metadata(require_ready=True)

    assert exc.value.code == NOT_READY_CODE


def test_admin_source_validation_endpoint_registers_canonical_sources(
    admin_client: TestClient,
) -> None:
    response = admin_client.post("/api/v1/admin/ingestion/sources/validate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["registered_count"] == 2
    assert payload["missing_count"] == 0
    assert len(payload["sources"]) == 2
    assert {source["source_type"] for source in payload["sources"]} == {"textbook", "solution_book"}

    sources_response = admin_client.get("/api/v1/admin/ingestion/sources")
    assert sources_response.status_code == 200
    sources = sources_response.json()
    assert len(sources) == 2
    assert all(source["canonical_source"] for source in sources)


def test_admin_embedding_readiness_and_prepare_endpoints(
    admin_client: TestClient,
) -> None:
    readiness_response = admin_client.get("/api/v1/admin/ingestion/embedding-readiness")
    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["ready_for_embedding"] is True
    assert readiness["textbook_missing_metadata_count"] == 0
    assert readiness["solution_chunks_total"] == 24

    prepare_response = admin_client.post(
        "/api/v1/admin/ingestion/prepare-reviewed-chunks",
        json={"write": False},
    )
    assert prepare_response.status_code == 200
    payload = prepare_response.json()
    assert payload["ready_for_embedding"] is True
    assert payload["counts"]["textbook_chunk_preview_missing_required_metadata"] == 0


def test_admin_reembed_refuses_when_reviewed_metadata_not_ready(
    admin_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata_path = tmp_path / "reviewed_curriculum_metadata.json"
    metadata_path.write_text(
        json.dumps({"ready_for_embedding": False, "version": "test"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.reviewed_curriculum_metadata.REVIEWED_METADATA_PATH", metadata_path)

    response = admin_client.post(
        "/api/v1/admin/rag/reembed",
        json={"batch_size": 10, "dry_run": True, "force": False, "resume_failed": False},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == NOT_READY_CODE
