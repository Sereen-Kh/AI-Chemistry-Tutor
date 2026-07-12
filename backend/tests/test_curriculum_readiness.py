from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin_curriculum import router
from app.core.dependencies import require_admin
from app.database import Base, get_db
from app.models.chemistry import Chapter, Lesson, Unit
from app.models.topic import Topic
from app.services.curriculum_readiness import validate_curriculum_readiness


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


def _reviewed_structure() -> dict:
    return {
        "units": [
            {
                "unit_id": "unit_04",
                "unit_number": 4,
                "unit_title": "الكيمياء اللاعضوية",
                "lessons": [
                    {
                        "lesson_id": "unit_04_lesson_01",
                        "lesson_number": "1",
                        "lesson_title": "المحاليل المائية",
                        "printed_page_start": 108,
                        "printed_page_end": 115,
                    }
                ],
            }
        ]
    }


def _seed_structure() -> dict:
    return {
        "units": [
            {
                "unit_number": 4,
                "title_ar": "الكيمياء اللاعضوية",
                "semester": 2,
                "chapters": [
                    {
                        "chapter_no": 1,
                        "order": 1,
                        "title_ar": "المحاليل",
                        "lessons": [
                            {
                                "lesson_no": 1,
                                "title_ar": "المحاليل المائية",
                                "book_pages": [108, 115],
                                "topics": [
                                    {
                                        "title_ar": "التركيز المولي",
                                        "order": 1,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _metadata() -> dict:
    return {"status": "reviewed", "version": "test-reviewed-v1"}


def _seed_database(db: Session) -> tuple[Unit, Chapter, Lesson, Topic]:
    unit = Unit(
        unit_number=4,
        semester=2,
        title_ar="الكيمياء اللاعضوية",
        order=4,
    )
    chapter = Chapter(unit=unit, title_ar="المحاليل", order=1)
    topic = Topic(title_ar="التركيز المولي", order=1)
    lesson = Lesson(
        chapter=chapter,
        title_ar="المحاليل المائية",
        content_ar="محتوى الدرس",
        order=1,
        page_start=108,
        page_end=115,
        topics=[topic],
    )
    db.add(lesson)
    db.commit()
    return unit, chapter, lesson, topic


def _validate(db: Session):
    return validate_curriculum_readiness(
        db,
        reviewed_structure=_reviewed_structure(),
        seed_structure=_seed_structure(),
        reviewed_metadata=_metadata(),
    )


def test_complete_curriculum_is_ready_and_maps_stable_lesson_id(db: Session) -> None:
    _seed_database(db)

    report = _validate(db)

    assert report.ready is True
    assert report.status == "ready"
    assert report.counts.errors == 0
    assert report.counts.mapped_lessons == 1
    assert report.lesson_mappings[0].stable_lesson_id == "unit_04_lesson_01"
    assert report.lesson_mappings[0].db_lesson_id is not None
    assert report.lesson_mappings[0].match_method == "title"


def test_missing_lesson_reports_exact_reviewed_stable_id(db: Session) -> None:
    unit = Unit(unit_number=4, semester=2, title_ar="الكيمياء اللاعضوية", order=4)
    db.add(Chapter(unit=unit, title_ar="المحاليل", order=1))
    db.commit()

    report = _validate(db)

    assert report.ready is False
    issue = next(row for row in report.issues if row.code == "DB_LESSON_MISSING")
    assert issue.stable_id == "unit_04_lesson_01"
    assert report.lesson_mappings[0].match_method == "unmatched"


def test_duplicate_order_and_title_page_mismatches_are_reported(db: Session) -> None:
    _unit, chapter, lesson, _topic = _seed_database(db)
    lesson.title_ar = "عنوان غير مطابق"
    lesson.page_start = 109
    db.add(
        Lesson(
            chapter=chapter,
            title_ar="درس إضافي",
            content_ar="محتوى",
            order=1,
            page_start=120,
            page_end=121,
        )
    )
    db.commit()

    report = _validate(db)
    codes = {row.code for row in report.issues}

    assert report.ready is False
    assert "DUPLICATE_LESSON_ORDER" in codes
    assert "DB_LESSON_TITLE_MISMATCH" in codes
    assert "DB_LESSON_PAGE_RANGE_MISMATCH" in codes
    assert "DB_LESSON_NOT_REVIEWED" in codes


def test_orphan_chapter_is_reported(db: Session) -> None:
    orphan = Chapter(unit_id=None, title_ar="فصل بلا وحدة", order=9)
    db.add(orphan)
    db.commit()

    report = _validate(db)

    assert report.ready is False
    assert any(row.code == "ORPHAN_CHAPTER" and row.entity_id == orphan.id for row in report.issues)


def test_admin_readiness_endpoint_is_read_only(db: Session) -> None:
    _seed_database(db)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_admin] = lambda: None
    before = db.scalar(select(func.count()).select_from(Lesson))

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/curriculum/readiness")

    after = db.scalar(select(func.count()).select_from(Lesson))
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "not_ready"}
    assert response.json()["artifacts"]["reviewed_book_structure"] == "data/processed/book_structure.json"
    assert response.json()["artifacts"]["canonical_curriculum_catalog"].endswith(
        "grade_9_chemistry_curriculum.reviewed.json"
    )
    assert before == after
