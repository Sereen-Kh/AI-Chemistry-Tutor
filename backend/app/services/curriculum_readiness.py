"""Read-only validation of the database curriculum against reviewed assets."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chemistry import Chapter, Lesson, Unit, lesson_topics
from app.models.topic import Topic
from app.schemas.curriculum_readiness import (
    CurriculumLessonMapping,
    CurriculumReadinessCounts,
    CurriculumReadinessIssue,
    CurriculumReadinessResponse,
)
from app.services.reviewed_curriculum_metadata import (
    ReviewedCurriculumMetadataError,
    load_reviewed_curriculum_metadata,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
REVIEWED_BOOK_STRUCTURE_PATH = REPO_ROOT / "data/processed/book_structure.json"
CANONICAL_CURRICULUM_PATH = (
    REPO_ROOT / "data/processed/curriculum/grade_9_chemistry_curriculum.reviewed.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _normalize_title(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    text = re.sub(r"[\u064b-\u065f\u0670ـ]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    return re.sub(r"[\s\-–—]+", " ", text).strip()


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _seed_lessons(unit: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (chapter, lesson)
        for chapter in unit.get("chapters") or []
        if isinstance(chapter, dict)
        for lesson in chapter.get("lessons") or []
        if isinstance(lesson, dict)
    ]


def _seed_page_range(lesson: dict[str, Any]) -> tuple[int | None, int | None]:
    pages = lesson.get("book_pages") or []
    if isinstance(pages, list) and pages:
        normalized = [_as_int(page) for page in pages]
        normalized = [page for page in normalized if page is not None]
        if normalized:
            return normalized[0], normalized[-1]
    return _as_int(lesson.get("printed_page_start")), _as_int(lesson.get("printed_page_end"))


def _append_issue(
    issues: list[CurriculumReadinessIssue],
    *,
    code: str,
    severity: str = "error",
    entity_type: str,
    message: str,
    entity_id: int | str | None = None,
    stable_id: str | None = None,
    field: str | None = None,
    expected: Any = None,
    actual: Any = None,
) -> None:
    issues.append(
        CurriculumReadinessIssue(
            code=code,
            severity=severity,
            entity_type=entity_type,
            message=message,
            entity_id=entity_id,
            stable_id=stable_id,
            field=field,
            expected=expected,
            actual=actual,
        )
    )


def _duplicate_values(values: list[int | None]) -> set[int]:
    counts = Counter(value for value in values if value is not None)
    return {int(value) for value, count in counts.items() if count > 1}


def validate_curriculum_readiness(
    db: Session,
    *,
    reviewed_structure: dict[str, Any] | None = None,
    seed_structure: dict[str, Any] | None = None,
    reviewed_metadata: dict[str, Any] | None = None,
) -> CurriculumReadinessResponse:
    """Compare current ORM rows with reviewed Grade 9 curriculum assets.

    The function performs SELECTs only. Optional payloads make deterministic tests
    independent of workstation files without creating a second validation path.
    """

    issues: list[CurriculumReadinessIssue] = []
    artifacts = {
        "reviewed_book_structure": _relative(REVIEWED_BOOK_STRUCTURE_PATH),
        "canonical_curriculum_catalog": _relative(CANONICAL_CURRICULUM_PATH),
    }

    if reviewed_structure is None:
        try:
            reviewed_structure = _read_json(REVIEWED_BOOK_STRUCTURE_PATH)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reviewed_structure = {"units": []}
            _append_issue(
                issues,
                code="REVIEWED_BOOK_STRUCTURE_INVALID",
                entity_type="artifact",
                message="Reviewed book structure is missing or invalid.",
                actual=str(exc),
            )
    if seed_structure is None:
        try:
            seed_structure = _read_json(CANONICAL_CURRICULUM_PATH)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            seed_structure = {"units": []}
            _append_issue(
                issues,
                code="CANONICAL_CURRICULUM_CATALOG_INVALID",
                entity_type="artifact",
                message="Canonical curriculum catalog is missing or invalid.",
                actual=str(exc),
            )
    if reviewed_metadata is None:
        try:
            reviewed_metadata = load_reviewed_curriculum_metadata(require_ready=False)
        except ReviewedCurriculumMetadataError as exc:
            reviewed_metadata = {}
            _append_issue(
                issues,
                code=exc.code,
                entity_type="artifact",
                message="Reviewed curriculum metadata is unavailable.",
            )

    metadata_version = str(reviewed_metadata.get("version") or "") or None
    if reviewed_metadata.get("status") != "reviewed":
        _append_issue(
            issues,
            code="REVIEWED_METADATA_STATUS_INVALID",
            entity_type="artifact",
            field="status",
            message="Curriculum metadata must have reviewed status.",
            expected="reviewed",
            actual=reviewed_metadata.get("status"),
        )
    if not metadata_version:
        _append_issue(
            issues,
            code="REVIEWED_METADATA_VERSION_MISSING",
            entity_type="artifact",
            field="version",
            message="Reviewed curriculum metadata version is missing.",
        )

    reviewed_units = [row for row in reviewed_structure.get("units") or [] if isinstance(row, dict)]
    seed_units = [row for row in seed_structure.get("units") or [] if isinstance(row, dict)]
    seed_units_by_number = {_as_int(row.get("unit_number")): row for row in seed_units}

    db_units = list(db.scalars(select(Unit).order_by(Unit.unit_number, Unit.id)).all())
    db_chapters = list(db.scalars(select(Chapter).order_by(Chapter.unit_id, Chapter.order, Chapter.id)).all())
    db_lessons = list(db.scalars(select(Lesson).order_by(Lesson.chapter_id, Lesson.order, Lesson.id)).all())
    db_topics = list(db.scalars(select(Topic).order_by(Topic.order, Topic.id)).all())
    links = list(
        db.execute(
            select(
                lesson_topics.c.lesson_id,
                lesson_topics.c.topic_id,
                lesson_topics.c.order,
            )
        ).all()
    )

    units_by_number: dict[int, list[Unit]] = defaultdict(list)
    chapters_by_unit: dict[int | None, list[Chapter]] = defaultdict(list)
    lessons_by_chapter: dict[int, list[Lesson]] = defaultdict(list)
    topics_by_lesson: dict[int, list[Topic]] = defaultdict(list)
    unit_ids = {row.id for row in db_units}
    chapter_ids = {row.id for row in db_chapters}
    lesson_by_id = {row.id: row for row in db_lessons}
    topic_by_id = {row.id: row for row in db_topics}

    for unit in db_units:
        units_by_number[unit.unit_number].append(unit)
    for chapter in db_chapters:
        chapters_by_unit[chapter.unit_id].append(chapter)
    for lesson in db_lessons:
        lessons_by_chapter[lesson.chapter_id].append(lesson)
    for link in links:
        lesson = lesson_by_id.get(link.lesson_id)
        topic = topic_by_id.get(link.topic_id)
        if lesson is None or topic is None:
            _append_issue(
                issues,
                code="BROKEN_LESSON_TOPIC_LINK",
                entity_type="relationship",
                entity_id=f"{link.lesson_id}:{link.topic_id}",
                message="Lesson-topic link references a missing row.",
            )
        else:
            topics_by_lesson[lesson.id].append(topic)

    for number, rows in units_by_number.items():
        if len(rows) > 1:
            _append_issue(
                issues,
                code="DUPLICATE_UNIT_NUMBER",
                entity_type="unit",
                entity_id=number,
                field="unit_number",
                message="More than one unit uses the same unit number.",
                actual=[row.id for row in rows],
            )
    for order in _duplicate_values([row.order for row in db_units]):
        _append_issue(
            issues,
            code="DUPLICATE_UNIT_ORDER",
            entity_type="unit",
            entity_id=order,
            field="order",
            message="More than one unit uses the same display order.",
        )
    for chapter in db_chapters:
        if chapter.unit_id is None or chapter.unit_id not in unit_ids:
            _append_issue(
                issues,
                code="ORPHAN_CHAPTER",
                entity_type="chapter",
                entity_id=chapter.id,
                field="unit_id",
                message="Chapter is not linked to an existing unit.",
                actual=chapter.unit_id,
            )
    for unit_id, rows in chapters_by_unit.items():
        for order in _duplicate_values([row.order for row in rows]):
            _append_issue(
                issues,
                code="DUPLICATE_CHAPTER_ORDER",
                entity_type="chapter",
                entity_id=f"{unit_id}:{order}",
                field="order",
                message="Chapters in one unit share the same order.",
            )
    for lesson in db_lessons:
        if lesson.chapter_id not in chapter_ids:
            _append_issue(
                issues,
                code="ORPHAN_LESSON",
                entity_type="lesson",
                entity_id=lesson.id,
                field="chapter_id",
                message="Lesson is not linked to an existing chapter.",
                actual=lesson.chapter_id,
            )
    for chapter_id, rows in lessons_by_chapter.items():
        for order in _duplicate_values([row.order for row in rows]):
            _append_issue(
                issues,
                code="DUPLICATE_LESSON_ORDER",
                entity_type="lesson",
                entity_id=f"{chapter_id}:{order}",
                field="order",
                message="Lessons in one chapter share the same order.",
            )
    for lesson_id, rows in topics_by_lesson.items():
        for order in _duplicate_values([row.order for row in rows]):
            _append_issue(
                issues,
                code="DUPLICATE_TOPIC_ORDER",
                entity_type="topic",
                entity_id=f"{lesson_id}:{order}",
                field="order",
                message="Topics linked to one lesson share the same order.",
            )

    stable_unit_ids = [str(row.get("unit_id") or "") for row in reviewed_units]
    for stable_id, count in Counter(stable_unit_ids).items():
        if not stable_id:
            _append_issue(
                issues,
                code="REVIEWED_UNIT_ID_MISSING",
                entity_type="unit",
                message="Reviewed unit is missing a stable unit ID.",
            )
        elif count > 1:
            _append_issue(
                issues,
                code="DUPLICATE_REVIEWED_UNIT_ID",
                entity_type="unit",
                stable_id=stable_id,
                message="Reviewed stable unit ID is duplicated.",
            )

    reviewed_lesson_ids = [
        str(lesson.get("lesson_id") or "")
        for unit in reviewed_units
        for lesson in unit.get("lessons") or []
        if isinstance(lesson, dict)
    ]
    for stable_id, count in Counter(reviewed_lesson_ids).items():
        if not stable_id:
            _append_issue(
                issues,
                code="REVIEWED_LESSON_ID_MISSING",
                entity_type="lesson",
                message="Reviewed lesson is missing a stable lesson ID.",
            )
        elif count > 1:
            _append_issue(
                issues,
                code="DUPLICATE_REVIEWED_LESSON_ID",
                entity_type="lesson",
                stable_id=stable_id,
                message="Reviewed stable lesson ID is duplicated.",
            )

    lesson_mappings: list[CurriculumLessonMapping] = []
    mapped_db_lesson_ids: set[int] = set()
    expected_chapter_count = 0
    expected_topic_count = 0

    for reviewed_unit in reviewed_units:
        stable_unit_id = str(reviewed_unit.get("unit_id") or "")
        unit_number = _as_int(reviewed_unit.get("unit_number"))
        expected_unit_title = str(reviewed_unit.get("unit_title") or "")
        seed_unit = seed_units_by_number.get(unit_number)
        db_unit_rows = units_by_number.get(unit_number or -1, [])
        db_unit = db_unit_rows[0] if db_unit_rows else None

        if seed_unit is None:
            _append_issue(
                issues,
                code="SEED_UNIT_MISSING",
                entity_type="unit",
                stable_id=stable_unit_id,
                message="Reviewed unit is absent from the seed structure.",
                expected=unit_number,
            )
        elif _normalize_title(seed_unit.get("title_ar")) != _normalize_title(expected_unit_title):
            _append_issue(
                issues,
                code="SEED_UNIT_TITLE_MISMATCH",
                entity_type="unit",
                stable_id=stable_unit_id,
                field="title_ar",
                message="Seed and reviewed unit titles differ.",
                expected=expected_unit_title,
                actual=seed_unit.get("title_ar"),
            )

        if db_unit is None:
            _append_issue(
                issues,
                code="DB_UNIT_MISSING",
                entity_type="unit",
                stable_id=stable_unit_id,
                message="Reviewed unit is missing from the database.",
                expected=unit_number,
            )
        elif _normalize_title(db_unit.title_ar) != _normalize_title(expected_unit_title):
            _append_issue(
                issues,
                code="DB_UNIT_TITLE_MISMATCH",
                entity_type="unit",
                entity_id=db_unit.id,
                stable_id=stable_unit_id,
                field="title_ar",
                message="Database and reviewed unit titles differ.",
                expected=expected_unit_title,
                actual=db_unit.title_ar,
            )

        seed_chapters = list(seed_unit.get("chapters") or []) if seed_unit else []
        expected_chapter_count += len(seed_chapters)
        expected_seed_lessons = _seed_lessons(seed_unit or {})
        db_unit_chapters = chapters_by_unit.get(db_unit.id, []) if db_unit else []
        db_unit_lessons = [lesson for chapter in db_unit_chapters for lesson in lessons_by_chapter.get(chapter.id, [])]

        for seed_chapter in seed_chapters:
            chapter_order = _as_int(seed_chapter.get("order") or seed_chapter.get("chapter_no"))
            db_chapter = next(
                (
                    row
                    for row in db_unit_chapters
                    if _normalize_title(row.title_ar) == _normalize_title(seed_chapter.get("title_ar"))
                ),
                None,
            ) or next((row for row in db_unit_chapters if row.order == chapter_order), None)
            if db_chapter is None:
                _append_issue(
                    issues,
                    code="DB_CHAPTER_MISSING",
                    entity_type="chapter",
                    stable_id=stable_unit_id,
                    message="Seed chapter is missing from the database unit.",
                    expected=seed_chapter.get("title_ar"),
                )
            elif _normalize_title(db_chapter.title_ar) != _normalize_title(seed_chapter.get("title_ar")):
                _append_issue(
                    issues,
                    code="DB_CHAPTER_TITLE_MISMATCH",
                    entity_type="chapter",
                    entity_id=db_chapter.id,
                    stable_id=stable_unit_id,
                    field="title_ar",
                    message="Database and seed chapter titles differ.",
                    expected=seed_chapter.get("title_ar"),
                    actual=db_chapter.title_ar,
                )

        previous_end: int | None = None
        for reviewed_lesson in reviewed_unit.get("lessons") or []:
            if not isinstance(reviewed_lesson, dict):
                continue
            stable_lesson_id = str(reviewed_lesson.get("lesson_id") or "")
            lesson_number = _as_int(reviewed_lesson.get("lesson_number"))
            expected_title = str(reviewed_lesson.get("lesson_title") or "")
            expected_start = _as_int(reviewed_lesson.get("printed_page_start"))
            expected_end = _as_int(reviewed_lesson.get("printed_page_end"))

            if expected_start is None or expected_end is None or expected_start > expected_end:
                _append_issue(
                    issues,
                    code="REVIEWED_LESSON_PAGE_RANGE_INVALID",
                    entity_type="lesson",
                    stable_id=stable_lesson_id,
                    field="printed_page_range",
                    message="Reviewed lesson page range is missing or invalid.",
                    expected=[expected_start, expected_end],
                )
            elif previous_end is not None and expected_start <= previous_end:
                _append_issue(
                    issues,
                    code="REVIEWED_LESSON_RANGE_OVERLAP",
                    entity_type="lesson",
                    stable_id=stable_lesson_id,
                    field="printed_page_range",
                    message="Reviewed lesson page range overlaps the preceding lesson.",
                    actual=[expected_start, expected_end],
                )
            if expected_end is not None:
                previous_end = max(previous_end or expected_end, expected_end)

            seed_match = next(
                (
                    item
                    for item in expected_seed_lessons
                    if _normalize_title(item[1].get("title_ar")) == _normalize_title(expected_title)
                ),
                None,
            ) or next(
                (
                    item
                    for item in expected_seed_lessons
                    if _as_int(item[1].get("lesson_no") or item[1].get("lesson_number")) == lesson_number
                ),
                None,
            )
            if seed_match is None:
                _append_issue(
                    issues,
                    code="SEED_LESSON_MISSING",
                    entity_type="lesson",
                    stable_id=stable_lesson_id,
                    message="Reviewed lesson is absent from the nested seed structure.",
                    expected=expected_title,
                )
                expected_topics: list[dict[str, Any]] = []
            else:
                seed_lesson = seed_match[1]
                expected_topics = [row for row in seed_lesson.get("topics") or [] if isinstance(row, dict)]
                seed_start, seed_end = _seed_page_range(seed_lesson)
                if _normalize_title(seed_lesson.get("title_ar")) != _normalize_title(expected_title):
                    _append_issue(
                        issues,
                        code="SEED_LESSON_TITLE_MISMATCH",
                        entity_type="lesson",
                        stable_id=stable_lesson_id,
                        field="title_ar",
                        message="Seed and reviewed lesson titles differ.",
                        expected=expected_title,
                        actual=seed_lesson.get("title_ar"),
                    )
                if (seed_start, seed_end) != (expected_start, expected_end):
                    _append_issue(
                        issues,
                        code="SEED_LESSON_PAGE_RANGE_MISMATCH",
                        entity_type="lesson",
                        stable_id=stable_lesson_id,
                        field="printed_page_range",
                        message="Seed and reviewed lesson page ranges differ.",
                        expected=[expected_start, expected_end],
                        actual=[seed_start, seed_end],
                    )
            expected_topic_count += len(expected_topics)

            db_lesson = next(
                (row for row in db_unit_lessons if _normalize_title(row.title_ar) == _normalize_title(expected_title)),
                None,
            )
            match_method = "title"
            if db_lesson is None:
                db_lesson = next((row for row in db_unit_lessons if row.order == lesson_number), None)
                match_method = "order" if db_lesson else "unmatched"

            lesson_mappings.append(
                CurriculumLessonMapping(
                    stable_lesson_id=stable_lesson_id,
                    unit_id=stable_unit_id,
                    db_lesson_id=db_lesson.id if db_lesson else None,
                    match_method=match_method,
                    expected_title=expected_title,
                    actual_title=db_lesson.title_ar if db_lesson else None,
                    expected_page_start=expected_start,
                    expected_page_end=expected_end,
                    actual_page_start=db_lesson.page_start if db_lesson else None,
                    actual_page_end=db_lesson.page_end if db_lesson else None,
                )
            )
            if db_lesson is None:
                _append_issue(
                    issues,
                    code="DB_LESSON_MISSING",
                    entity_type="lesson",
                    stable_id=stable_lesson_id,
                    message="Reviewed lesson is missing from the database.",
                    expected=expected_title,
                )
                continue

            mapped_db_lesson_ids.add(db_lesson.id)
            if _normalize_title(db_lesson.title_ar) != _normalize_title(expected_title):
                _append_issue(
                    issues,
                    code="DB_LESSON_TITLE_MISMATCH",
                    entity_type="lesson",
                    entity_id=db_lesson.id,
                    stable_id=stable_lesson_id,
                    field="title_ar",
                    message="Database and reviewed lesson titles differ.",
                    expected=expected_title,
                    actual=db_lesson.title_ar,
                )
            if (db_lesson.page_start, db_lesson.page_end) != (expected_start, expected_end):
                _append_issue(
                    issues,
                    code="DB_LESSON_PAGE_RANGE_MISMATCH",
                    entity_type="lesson",
                    entity_id=db_lesson.id,
                    stable_id=stable_lesson_id,
                    field="printed_page_range",
                    message="Database and reviewed lesson page ranges differ.",
                    expected=[expected_start, expected_end],
                    actual=[db_lesson.page_start, db_lesson.page_end],
                )

            linked_titles = {_normalize_title(row.title_ar) for row in topics_by_lesson.get(db_lesson.id, [])}
            for expected_topic in expected_topics:
                topic_title = str(expected_topic.get("title_ar") or "")
                if _normalize_title(topic_title) not in linked_titles:
                    _append_issue(
                        issues,
                        code="DB_TOPIC_LINK_MISSING",
                        entity_type="topic",
                        entity_id=db_lesson.id,
                        stable_id=stable_lesson_id,
                        message="Expected topic is not linked to the database lesson.",
                        expected=topic_title,
                    )

    reviewed_unit_numbers = {_as_int(row.get("unit_number")) for row in reviewed_units}
    for unit in db_units:
        if unit.unit_number not in reviewed_unit_numbers:
            _append_issue(
                issues,
                code="DB_UNIT_NOT_REVIEWED",
                entity_type="unit",
                entity_id=unit.id,
                message="Database unit is outside the reviewed Grade 9 contract.",
                actual=unit.unit_number,
            )
    for lesson in db_lessons:
        if lesson.id not in mapped_db_lesson_ids:
            _append_issue(
                issues,
                code="DB_LESSON_NOT_REVIEWED",
                entity_type="lesson",
                entity_id=lesson.id,
                message="Database lesson does not map to a reviewed stable lesson ID.",
                actual=lesson.title_ar,
            )

    error_count = sum(issue.severity == "error" for issue in issues)
    warning_count = sum(issue.severity == "warning" for issue in issues)
    counts = CurriculumReadinessCounts(
        expected_units=len(reviewed_units),
        database_units=len(db_units),
        expected_chapters=expected_chapter_count,
        database_chapters=len(db_chapters),
        expected_lessons=len(reviewed_lesson_ids),
        database_lessons=len(db_lessons),
        mapped_lessons=len(mapped_db_lesson_ids),
        expected_topics=expected_topic_count,
        database_topics=len(db_topics),
        linked_topics=len(links),
        errors=error_count,
        warnings=warning_count,
    )
    ready = error_count == 0
    return CurriculumReadinessResponse(
        status="ready" if ready else "not_ready",
        ready=ready,
        checked_at=datetime.now(timezone.utc),
        reviewed_metadata_version=metadata_version,
        artifacts=artifacts,
        counts=counts,
        lesson_mappings=lesson_mappings,
        issues=issues,
    )
