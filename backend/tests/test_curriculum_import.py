from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.chemistry import Lesson, Unit
from app.models.curriculum_mapping import CurriculumEntityMapping
from app.schemas.curriculum_catalog import ReviewedCurriculumCatalog
from app.services import curriculum_import
from app.services.curriculum_import import import_reviewed_curriculum, load_canonical_curriculum_catalog
from app.services.curriculum_readiness import validate_curriculum_readiness
from app.services.reviewed_curriculum_catalog import build_reviewed_curriculum_catalog


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _catalog() -> ReviewedCurriculumCatalog:
    return ReviewedCurriculumCatalog.model_validate(
        {
            "reviewed_metadata_version": "test-reviewed-v1",
            "generated_at": datetime.now(timezone.utc),
            "source_paths": ["test-fixture.json"],
            "units": [
                {
                    "stable_id": "unit_04",
                    "unit_number": 4,
                    "semester": 2,
                    "title_ar": "الكيمياء اللاعضوية",
                    "order": 4,
                    "chapters": [
                        {
                            "stable_id": "unit_04_chapter_01",
                            "chapter_number": 1,
                            "title_ar": "المحاليل",
                            "order": 1,
                            "lessons": [
                                {
                                    "stable_id": "unit_04_lesson_01",
                                    "lesson_number": 1,
                                    "title_ar": "المحاليل المائية",
                                    "order": 1,
                                    "printed_page_start": 108,
                                    "printed_page_end": 115,
                                    "pdf_page_start": 2,
                                    "pdf_page_end": 9,
                                    "quality_status": "ready",
                                    "quality_score": 1.0,
                                    "topics": [
                                        {
                                            "stable_id": "unit_04_lesson_01_subtopic_001",
                                            "title_ar": "التركيز المولي",
                                            "order": 1,
                                            "page_start": 108,
                                            "page_end": 113,
                                            "quality_status": "ready",
                                            "quality_score": 1.0,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )


def test_real_reviewed_catalog_has_complete_9_lesson_52_topic_contract() -> None:
    catalog = build_reviewed_curriculum_catalog()

    lessons = [lesson for unit in catalog.units for chapter in unit.chapters for lesson in chapter.lessons]
    topics = [topic for lesson in lessons for topic in lesson.topics]
    assert len(catalog.units) == 3
    assert len(lessons) == 9
    assert len(topics) == 52
    assert {lesson.stable_id for lesson in lessons} >= {
        "unit_05_lesson_03",
        "unit_06_lesson_01",
    }


def test_dry_run_reports_counts_without_writing(db: Session) -> None:
    report = import_reviewed_curriculum(db, catalog=_catalog(), dry_run=True)

    assert report.status == "dry_run"
    assert report.counts.inserted == 4
    assert report.counts.mappings_inserted == 4
    assert db.scalar(select(func.count()).select_from(Unit)) == 0
    assert db.scalar(select(func.count()).select_from(CurriculumEntityMapping)) == 0


def test_two_imports_are_idempotent_and_preserve_numeric_ids(db: Session) -> None:
    first = import_reviewed_curriculum(db, catalog=_catalog(), dry_run=False)
    lesson_id = db.scalar(select(Lesson.id))

    second = import_reviewed_curriculum(db, catalog=_catalog(), dry_run=False)

    assert first.status == "applied"
    assert first.counts.inserted == 4
    assert first.counts.mappings_inserted == 4
    assert second.counts.inserted == 0
    assert second.counts.updated == 0
    assert second.counts.unchanged == 4
    assert second.counts.mappings_inserted == 0
    assert second.counts.mappings_updated == 0
    assert second.counts.mappings_unchanged == 4
    assert db.scalar(select(Lesson.id)) == lesson_id


def test_import_does_not_remove_unreviewed_rows(db: Session) -> None:
    extra = Unit(unit_number=99, semester=2, title_ar="وحدة تجريبية", order=99)
    db.add(extra)
    db.commit()

    import_reviewed_curriculum(db, catalog=_catalog(), dry_run=False)

    assert db.scalar(select(func.count()).select_from(Unit)) == 2
    assert db.scalar(select(Unit.id).where(Unit.unit_number == 99)) == extra.id


def test_mapping_conflict_stops_before_writes(db: Session) -> None:
    db.add(
        CurriculumEntityMapping(
            entity_type="lesson",
            stable_id="unit_04_lesson_01",
            entity_id=999,
            reviewed_metadata_version="old",
            source_path="old.json",
            metadata_json={},
        )
    )
    db.commit()

    report = import_reviewed_curriculum(db, catalog=_catalog(), dry_run=False)

    assert report.status == "conflict"
    assert report.counts.conflicting == 1
    assert report.conflicts[0].code == "MAPPING_TARGET_MISSING"
    assert db.scalar(select(func.count()).select_from(Unit)) == 0


def test_apply_failure_rolls_back_all_curriculum_rows(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    original = curriculum_import._upsert_mapping

    def fail_after_mapping(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("simulated import failure")

    monkeypatch.setattr(curriculum_import, "_upsert_mapping", fail_after_mapping)

    with pytest.raises(RuntimeError, match="simulated import failure"):
        import_reviewed_curriculum(db, catalog=_catalog(), dry_run=False)

    assert db.scalar(select(func.count()).select_from(Unit)) == 0
    assert db.scalar(select(func.count()).select_from(CurriculumEntityMapping)) == 0


def test_full_canonical_import_passes_curriculum_readiness(db: Session) -> None:
    catalog = load_canonical_curriculum_catalog()

    result = import_reviewed_curriculum(db, catalog=catalog, dry_run=False)
    readiness = validate_curriculum_readiness(db)

    assert result.counts.inserted == 67
    assert result.counts.mappings_inserted == 67
    assert readiness.status == "ready"
    assert readiness.counts.database_units == 3
    assert readiness.counts.database_lessons == 9
    assert readiness.counts.database_topics == 52

