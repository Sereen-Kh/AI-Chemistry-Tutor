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
from app.models.textbook import RagChunk
from app.services.reviewed_curriculum_metadata import (
    NOT_READY_CODE,
    ReviewedCurriculumMetadataError,
    load_reviewed_curriculum_metadata,
)
from app.services.reviewed_ingestion_assets import (
    canonical_source_statuses,
    load_reviewed_chunks_to_rag,
    prepare_reviewed_chunks,
    rag_source_statuses,
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


def test_rag_source_status_includes_filesystem_and_reviewed_artifact_state() -> None:
    sources = rag_source_statuses()

    by_id = {source["id"]: source for source in sources}
    assert set(by_id) == {"textbook", "solution_book"}
    assert by_id["textbook"]["filename"] == "Chemistry.pdf"
    assert by_id["textbook"]["page_count"] == 96
    assert by_id["textbook"]["checksum_sha256"] == "3e94fe8be9d4c750c0253d3b81dc12ddf826ec6c901a2def17427d32cb5f9187"
    assert by_id["textbook"]["file_size_bytes"] > 100_000_000
    assert by_id["textbook"]["last_modified_at"]
    assert by_id["textbook"]["extraction_status"] == "complete"
    assert by_id["textbook"]["chunk_status"] == "partial"
    assert by_id["textbook"]["counts"]["missing_chunk_pages"] == 7
    assert by_id["solution_book"]["filename"] == "Chemistry_Solution_Book.pdf"
    assert by_id["solution_book"]["page_count"] == 35
    assert by_id["solution_book"]["chunk_status"] == "complete"


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


def test_load_reviewed_chunks_to_rag_inserts_pending_db_rows(admin_db: Session) -> None:
    result = load_reviewed_chunks_to_rag(admin_db, clear_existing=True)

    assert result["status"] == "loaded"
    assert result["chunks_inserted"] == 744
    assert result["sources"]["textbook"]["chunks_inserted"] == 720
    assert result["sources"]["solution_book"]["chunks_inserted"] == 24
    assert result["skipped_blocked"] == 0
    assert result["skipped_missing_metadata"] == 0

    rows = admin_db.query(RagChunk).all()
    assert len(rows) == 744
    assert {row.embedding_status for row in rows} == {"pending"}
    assert {row.embedding for row in rows} == {None}

    textbook = next(row for row in rows if row.source_type == "textbook")
    assert textbook.metadata_json["unit_id"] == "unit_04"
    assert textbook.metadata_json["lesson_id"] == "unit_04_lesson_01"
    assert textbook.metadata_json["quality_status"] == "ready"
    assert textbook.metadata_json["reviewed_metadata_version"] == "2026-06-reviewed-v1"


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


def test_admin_rag_sources_endpoints_and_scan_register_source(
    admin_client: TestClient,
) -> None:
    response = admin_client.get("/api/v1/admin/rag/sources")
    assert response.status_code == 200
    sources = response.json()
    assert {source["id"] for source in sources} == {"textbook", "solution_book"}
    textbook = next(source for source in sources if source["id"] == "textbook")
    assert textbook["db_source_id"] is None
    assert textbook["ingestion_status"] == "not_registered"
    assert textbook["page_count"] == 96
    assert textbook["checksum_sha256"]

    detail_response = admin_client.get("/api/v1/admin/rag/sources/textbook")
    assert detail_response.status_code == 200
    assert detail_response.json()["filename"] == "Chemistry.pdf"

    scan_response = admin_client.post("/api/v1/admin/rag/sources/textbook/scan")
    assert scan_response.status_code == 200
    scanned = scan_response.json()
    assert scanned["id"] == "textbook"
    assert scanned["db_source_id"] is not None
    assert scanned["ingestion_status"] == "reviewed_source_ready"

    numeric_response = admin_client.get(f"/api/v1/admin/rag/sources/{scanned['db_source_id']}")
    assert numeric_response.status_code == 200
    assert numeric_response.json()["id"] == "textbook"

    missing_response = admin_client.get("/api/v1/admin/rag/sources/not-a-source")
    assert missing_response.status_code == 404


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


def test_admin_load_reviewed_chunks_endpoint(admin_client: TestClient, admin_db: Session) -> None:
    response = admin_client.post(
        "/api/v1/admin/ingestion/load-reviewed-chunks",
        json={"clear_existing": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["chunks_inserted"] == 744
    assert payload["embedding_status"] == "pending"
    assert admin_db.query(RagChunk).count() == 744


def test_admin_rag_chunk_explorer_reports_readiness_counts(
    admin_client: TestClient,
    admin_db: Session,
) -> None:
    load_reviewed_chunks_to_rag(admin_db, clear_existing=True)

    response = admin_client.get("/api/v1/admin/rag/chunks?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 744
    assert len(payload["items"]) == 5
    assert payload["counts"]["total_chunks"] == 744
    assert payload["counts"]["ready_chunks"] == 677
    assert payload["counts"]["needs_review_chunks"] == 67
    assert payload["counts"]["blocked_chunks"] == 0
    assert payload["counts"]["missing_metadata_chunks"] == 0
    assert payload["counts"]["pending_chunks"] == 744

    first = payload["items"][0]
    assert first["source_type"] in {"textbook", "solution_book"}
    assert first["quality_status"] in {"ready", "needs_review"}
    assert first["reviewed_metadata_version"] == "2026-06-reviewed-v1"
    assert first["embedding_status"] == "pending"
    assert first["embedding_allowed"] is True
    assert first["rag_search_allowed"] is True
    assert first["student_generation_allowed"] is (first["quality_status"] == "ready")
    assert first["warning_required"] is (first["quality_status"] == "needs_review")
    assert first["reason_codes"]
    assert first["legacy_unmapped"] is False
    assert first["content_preview"]


def test_admin_rag_chunk_explorer_filters_needs_review_solution_chunks(
    admin_client: TestClient,
    admin_db: Session,
) -> None:
    load_reviewed_chunks_to_rag(admin_db, clear_existing=True)

    response = admin_client.get(
        "/api/v1/admin/rag/chunks",
        params={"source_type": "solution_book", "quality_status": "needs_review", "limit": 50},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 17
    assert payload["filtered_total"] == 17
    assert payload["global_counts"]["total_chunks"] == 744
    assert len(payload["items"]) == 17
    assert {item["source_type"] for item in payload["items"]} == {"solution_book"}
    assert {item["quality_status"] for item in payload["items"]} == {"needs_review"}
    assert all(item["missing_metadata"] == [] for item in payload["items"])
    assert all(item["embedding_allowed"] is True for item in payload["items"])
    assert all(item["rag_search_allowed"] is True for item in payload["items"])
    assert all(item["student_generation_allowed"] is False for item in payload["items"])
    assert all(item["warning_required"] is True for item in payload["items"])


def test_admin_chunk_explorer_supports_detail_and_metadata_filters(
    admin_client: TestClient,
    admin_db: Session,
) -> None:
    load_reviewed_chunks_to_rag(admin_db, clear_existing=True)

    sample = admin_client.get(
        "/api/v1/admin/rag/chunks",
        params={"source_type": "textbook", "limit": 1},
    )
    sample_item = sample.json()["items"][0]
    filtered = admin_client.get(
        "/api/v1/admin/rag/chunks",
        params={
            "source_type": "textbook",
            "content_type": sample_item["content_type"],
            "search": sample_item["content_preview"][:4],
            "limit": 5,
        },
    )

    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["filtered_total"] == payload["total"]
    assert payload["global_counts"]["total_chunks"] == 744
    assert all(sample_item["content_preview"][:4] in item["content_preview"] for item in payload["items"])
    assert all(item["source_file"] for item in payload["items"])
    assert all(item["content_hash"] for item in payload["items"])

    chunk_id = payload["items"][0]["id"]
    detail = admin_client.get(f"/api/v1/admin/rag/chunks/{chunk_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == chunk_id
    assert detail.json()["metadata_json"]["reviewed_metadata_version"] == "2026-06-reviewed-v1"


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
