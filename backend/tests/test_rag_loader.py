from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.textbook import ContentSource, RagChunk
from app.services import reviewed_ingestion_assets as assets


@pytest.fixture()
def loader_db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all(
        [
            ContentSource(
                source_type="textbook",
                title="Textbook",
                file_path=assets.TEXTBOOK_PDF,
                status="ready",
            ),
            ContentSource(
                source_type="solution_book",
                title="Solutions",
                file_path=assets.SOLUTION_BOOK_PDF,
                status="ready",
            ),
        ]
    )
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def reviewed_loader(monkeypatch: pytest.MonkeyPatch):
    rows = [
        {
            "chunk_id": "textbook-001",
            "content": "تعريف كيميائي أول.",
            "unit_id": "unit_04",
            "lesson_id": "unit_04_lesson_01",
            "source_type": "textbook",
            "printed_page_start": 108,
            "printed_page_end": 108,
            "quality_status": "ready",
            "reviewed_metadata_version": "test-v1",
            "chunk_type": "concept",
        },
        {
            "chunk_id": "textbook-002",
            "content": "تعريف كيميائي ثان.",
            "unit_id": "unit_04",
            "lesson_id": "unit_04_lesson_01",
            "source_type": "textbook",
            "printed_page_start": 109,
            "printed_page_end": 109,
            "quality_status": "ready",
            "reviewed_metadata_version": "test-v1",
            "chunk_type": "concept",
        },
    ]
    metadata = {
        "version": "test-v1",
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
    monkeypatch.setattr(assets, "ensure_reviewed_metadata_ready", lambda: metadata)
    monkeypatch.setattr(assets, "validate_canonical_sources", lambda **_kwargs: None)
    monkeypatch.setattr(assets, "_reviewed_chunk_rows_for_source", lambda source_type: rows if source_type == "textbook" else [])
    return rows


def test_loader_is_idempotent_and_preserves_unchanged_embeddings(
    loader_db: Session,
    reviewed_loader,
) -> None:
    first = assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)
    assert first["chunks_inserted"] == 2
    assert first["chunks_updated"] == 0

    rows = loader_db.query(RagChunk).order_by(RagChunk.chunk_index).all()
    rows[0].embedding = [0.0] * 768
    rows[0].embedding_status = "completed"
    loader_db.commit()

    second = assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)
    assert second["chunks_inserted"] == 0
    assert second["chunks_updated"] == 0
    assert second["chunks_unchanged"] == 2

    refreshed = loader_db.query(RagChunk).order_by(RagChunk.chunk_index).first()
    assert refreshed is not None
    assert refreshed.embedding_status == "completed"
    assert refreshed.embedding is not None


def test_loader_resets_only_changed_content_embedding(
    loader_db: Session,
    reviewed_loader,
) -> None:
    assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)
    reviewed_loader[0]["content"] = "تعريف كيميائي محدث."

    result = assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)

    assert result["chunks_updated"] == 1
    assert result["embedding_reset"] == 1
    first, second = loader_db.query(RagChunk).order_by(RagChunk.chunk_index).all()
    assert first.content == "تعريف كيميائي محدث."
    assert first.embedding_status == "pending"
    assert second.embedding_status == "pending"


def test_loader_marks_removed_reviewed_rows_stale(
    loader_db: Session,
    reviewed_loader,
) -> None:
    assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)
    reviewed_loader.pop()

    result = assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)

    assert result["chunks_stale"] == 1
    rows = loader_db.query(RagChunk).order_by(RagChunk.chunk_index).all()
    assert len(rows) == 2
    assert rows[1].embedding_status == "skipped"
    assert rows[1].embedding_error == "stale_reviewed_chunk"
    assert rows[1].metadata_json["stale"] is True


def test_loader_dry_run_does_not_write_rows(
    loader_db: Session,
    reviewed_loader,
) -> None:
    result = assets.load_reviewed_chunks_to_rag(
        loader_db,
        dry_run=True,
        include_solution_book=False,
    )

    assert result["status"] == "dry_run"
    assert result["would_write"] is True
    assert result["chunks_inserted"] == 2
    assert loader_db.query(RagChunk).count() == 0


def test_loader_dry_run_works_before_source_registration(
    loader_db: Session,
    reviewed_loader,
) -> None:
    loader_db.query(ContentSource).delete(synchronize_session=False)
    loader_db.commit()

    result = assets.load_reviewed_chunks_to_rag(
        loader_db,
        dry_run=True,
        include_solution_book=False,
    )

    assert result["status"] == "dry_run"
    assert result["chunks_inserted"] == 2
    assert loader_db.query(ContentSource).count() == 0
    assert loader_db.query(RagChunk).count() == 0


def test_loader_rejects_clear_existing_on_postgresql(
    loader_db: Session,
    reviewed_loader,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Dialect:
        name = "postgresql"

    monkeypatch.setattr(loader_db, "get_bind", lambda: type("Bind", (), {"dialect": Dialect()})())

    with pytest.raises(ValueError, match="CLEAR_EXISTING_DISABLED_IN_PRODUCTION"):
        assets.load_reviewed_chunks_to_rag(
            loader_db,
            clear_existing=True,
            include_solution_book=False,
        )


def test_loader_removes_vector_from_existing_blocked_chunk(
    loader_db: Session,
    reviewed_loader,
) -> None:
    assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)
    existing = loader_db.query(RagChunk).order_by(RagChunk.id).first()
    assert existing is not None
    existing.embedding = [0.0] * 768
    existing.embedding_status = "completed"
    loader_db.commit()

    reviewed_loader[0]["quality_status"] = "blocked"
    result = assets.load_reviewed_chunks_to_rag(loader_db, include_solution_book=False)

    assert result["skipped_blocked"] == 1
    refreshed = loader_db.get(RagChunk, existing.id)
    assert refreshed is not None
    assert refreshed.embedding is None
    assert refreshed.embedding_status == "skipped"
