"""Admin ingestion durability and retry regression tests."""

from __future__ import annotations

import asyncio
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
from app.models.ingestion import IngestionJob, IngestionPage
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk
from app.services.ingestion_pipeline import retry_ingestion_page


@pytest.fixture()
def ingestion_db() -> Iterator[Session]:
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
def ingestion_client(ingestion_db: Session) -> Iterator[TestClient]:
    def override_db():
        yield ingestion_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_admin] = lambda: None
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_admin, None)


def test_ingestion_status_reads_db_not_memory(
    ingestion_client: TestClient,
    ingestion_db: Session,
) -> None:
    source = ContentSource(source_type="textbook", title="Chemistry", status="processing")
    ingestion_db.add(source)
    ingestion_db.commit()
    ingestion_db.refresh(source)
    job = IngestionJob(
        job_uid="durable-job-1",
        source_id=source.id,
        status="running",
        progress=45,
        message="Processing page 2",
        result_json={"total_pages": 3, "pages_processed": 1, "warnings": ["slow page"]},
        errors_json=[],
    )
    ingestion_db.add(job)
    ingestion_db.commit()
    ingestion_db.refresh(job)
    ingestion_db.add_all(
        [
            IngestionPage(source_id=source.id, job_id=job.id, page_number=1, page_type="SELECTABLE_TEXT", status="completed_text_only"),
            IngestionPage(source_id=source.id, job_id=job.id, page_number=2, page_type="NEEDS_VISION", status="failed"),
        ]
    )
    ingestion_db.commit()

    response = ingestion_client.get("/api/v1/admin/ingestion/status/durable-job-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "durable-job-1"
    assert payload["job_uid"] == "durable-job-1"
    assert payload["status"] == "running"
    assert payload["progress"] == 45
    assert payload["pages"]["total"] == 2
    assert payload["pages"]["failed"] == 1
    assert len(payload["page_statuses"]) == 2


def test_retry_page_rebuilds_without_duplicate_chunks(
    ingestion_db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ContentSource(source_type="textbook", title="Chemistry", status="failed")
    ingestion_db.add(source)
    ingestion_db.commit()
    ingestion_db.refresh(source)
    cache_path = tmp_path / "page_001.json"
    cache_path.write_text(
        json.dumps(
            {
                "page_number": 1,
                "page_type": "SELECTABLE_TEXT",
                "status": "completed_text_only",
                "extraction_methods": ["pymupdf"],
                "extraction_method": "pymupdf",
                "sections": [{"content": "محتوى مستعاد للصفحة", "content_type": "text"}],
                "questions": [],
                "warnings": [],
                "errors": [],
                "char_count": 42,
                "completeness_score": 1.0,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    page = IngestionPage(
        source_id=source.id,
        page_number=1,
        page_type="SELECTABLE_TEXT",
        status="failed",
        cache_path=str(cache_path),
    )
    ingestion_db.add(page)
    ingestion_db.add(
        RagChunk(
            source_id=source.id,
            page_number=1,
            chunk_index=0,
            content="old chunk",
            normalized_content="old chunk",
            content_type="text",
            source_type="textbook",
        )
    )
    ingestion_db.add(
        ExtractedQuestion(
            source_id=source.id,
            page_number=1,
            question_text="old question",
            question_type="short_answer",
            answer_source="unknown",
        )
    )
    ingestion_db.commit()
    ingestion_db.refresh(page)

    async def fake_store_chunks(db, source, page_num, _payload, _chapter_id, _lesson_id, _topic_id, _method, chunk_index_start, **_kwargs):
        assert db.query(RagChunk).filter(RagChunk.source_id == source.id, RagChunk.page_number == page_num).count() == 0
        db.add(
            RagChunk(
                source_id=source.id,
                page_number=page_num,
                chunk_index=chunk_index_start,
                content="new chunk",
                normalized_content="new chunk",
                content_type="text",
                source_type=source.source_type,
                embedding_status="completed",
            )
        )
        return 1

    def fake_store_questions(db, source, page_num, _payload, _chapter_id, _lesson_id, _topic_id):
        assert db.query(ExtractedQuestion).filter(ExtractedQuestion.source_id == source.id, ExtractedQuestion.page_number == page_num).count() == 0
        db.add(
            ExtractedQuestion(
                source_id=source.id,
                page_number=page_num,
                question_text="new question",
                question_type="short_answer",
                answer_source="page",
                needs_review=False,
            )
        )
        return 1

    monkeypatch.setattr("app.services.ingestion_pipeline._store_page_chunks", fake_store_chunks)
    monkeypatch.setattr("app.services.ingestion_pipeline._store_questions", fake_store_questions)

    result = asyncio.run(retry_ingestion_page(ingestion_db, page))

    assert result["status"] == "completed_text_only"
    assert result["chunks_deleted"] == 1
    assert result["questions_deleted"] == 1
    assert ingestion_db.query(RagChunk).filter(RagChunk.source_id == source.id, RagChunk.page_number == 1).count() == 1
    assert ingestion_db.query(RagChunk).filter(RagChunk.content == "new chunk").count() == 1
    assert ingestion_db.query(ExtractedQuestion).filter(ExtractedQuestion.question_text == "new question").count() == 1
