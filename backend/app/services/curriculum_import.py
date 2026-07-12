"""Transactional, idempotent import of the canonical reviewed curriculum."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.chemistry import Chapter, Lesson, Unit
from app.models.curriculum_mapping import CurriculumEntityMapping
from app.models.topic import Topic
from app.schemas.curriculum_catalog import (
    CurriculumImportConflict,
    CurriculumImportCounts,
    CurriculumImportReport,
    ReviewedCurriculumCatalog,
)
from app.services.curriculum_readiness import REPO_ROOT
from app.services.reviewed_curriculum_catalog import CANONICAL_CURRICULUM_PATH


class CurriculumImportError(RuntimeError):
    pass


class CurriculumImportConflictError(CurriculumImportError):
    def __init__(self, conflicts: list[CurriculumImportConflict]) -> None:
        self.conflicts = conflicts
        super().__init__("CURRICULUM_IMPORT_CONFLICT")


def load_canonical_curriculum_catalog(
    path: Path = CANONICAL_CURRICULUM_PATH,
) -> ReviewedCurriculumCatalog:
    if not path.exists():
        raise CurriculumImportError(f"CURRICULUM_CATALOG_MISSING: {path}")
    try:
        return ReviewedCurriculumCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise CurriculumImportError(f"CURRICULUM_CATALOG_INVALID: {exc}") from exc


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _different(entity: Any, values: dict[str, Any]) -> bool:
    return any(getattr(entity, field) != value for field, value in values.items())


def _content_ar(page_start: int, page_end: int, topic_titles: list[str]) -> str:
    page_label = str(page_start) if page_start == page_end else f"{page_start}-{page_end}"
    lines = [f"صفحات الكتاب: {page_label}", "الموضوعات:"]
    lines.extend(f"- {title}" for title in topic_titles)
    return "\n".join(lines)


def _mapping_for_stable_id(
    db: Session,
    entity_type: str,
    stable_id: str,
) -> CurriculumEntityMapping | None:
    return (
        db.query(CurriculumEntityMapping)
        .filter(
            CurriculumEntityMapping.entity_type == entity_type,
            CurriculumEntityMapping.stable_id == stable_id,
        )
        .one_or_none()
    )


def _mapped_entity(
    db: Session,
    entity_type: str,
    stable_id: str,
    model,
    conflicts: list[CurriculumImportConflict],
):
    mapping = _mapping_for_stable_id(db, entity_type, stable_id)
    if mapping is None:
        return None
    entity = db.get(model, mapping.entity_id)
    if entity is None:
        conflicts.append(
            CurriculumImportConflict(
                code="MAPPING_TARGET_MISSING",
                entity_type=entity_type,
                stable_id=stable_id,
                existing_entity_id=mapping.entity_id,
                message="Stable ID mapping points to a missing database row.",
            )
        )
    return entity


def _mapping_values(
    *,
    version: str,
    source_path: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "reviewed_metadata_version": version,
        "source_path": source_path,
        "metadata_json": metadata,
    }


def _upsert_mapping(
    db: Session,
    *,
    entity_type: str,
    stable_id: str,
    entity_id: int,
    version: str,
    source_path: str,
    metadata: dict[str, Any],
    counts: CurriculumImportCounts,
    stable_mapping: dict[str, int],
) -> None:
    mapping = _mapping_for_stable_id(db, entity_type, stable_id)
    values = _mapping_values(version=version, source_path=source_path, metadata=metadata)
    stable_mapping[stable_id] = entity_id
    if mapping is None:
        db.add(
            CurriculumEntityMapping(
                entity_type=entity_type,
                stable_id=stable_id,
                entity_id=entity_id,
                **values,
            )
        )
        counts.mappings_inserted += 1
        return
    changed = mapping.entity_id != entity_id or _different(mapping, values)
    if changed:
        mapping.entity_id = entity_id
        for field, value in values.items():
            setattr(mapping, field, value)
        counts.mappings_updated += 1
    else:
        counts.mappings_unchanged += 1


def _record_entity_change(
    entity: Any | None,
    values: dict[str, Any],
    counts: CurriculumImportCounts,
) -> None:
    if entity is None:
        counts.inserted += 1
    elif _different(entity, values):
        counts.updated += 1
    else:
        counts.unchanged += 1


def _inspect_catalog(
    db: Session,
    catalog: ReviewedCurriculumCatalog,
) -> tuple[CurriculumImportCounts, list[CurriculumImportConflict], dict[str, int]]:
    counts = CurriculumImportCounts()
    conflicts: list[CurriculumImportConflict] = []
    stable_mapping: dict[str, int] = {}
    version = catalog.reviewed_metadata_version
    source_path = _relative(CANONICAL_CURRICULUM_PATH)

    for unit_data in catalog.units:
        unit = _mapped_entity(db, "unit", unit_data.stable_id, Unit, conflicts)
        natural = db.query(Unit).filter(Unit.unit_number == unit_data.unit_number).one_or_none()
        unit = unit or natural
        unit_values = {
            "unit_number": unit_data.unit_number,
            "semester": unit_data.semester,
            "title_ar": unit_data.title_ar,
            "order": unit_data.order,
        }
        _record_entity_change(unit, unit_values, counts)
        if unit is not None:
            stable_mapping[unit_data.stable_id] = unit.id
        mapping = _mapping_for_stable_id(db, "unit", unit_data.stable_id)
        if mapping is None:
            counts.mappings_inserted += 1
        elif unit is not None:
            values = _mapping_values(
                version=version,
                source_path=source_path,
                metadata={"unit_number": unit_data.unit_number, "title_ar": unit_data.title_ar},
            )
            if mapping.entity_id != unit.id or _different(mapping, values):
                counts.mappings_updated += 1
            else:
                counts.mappings_unchanged += 1

        for chapter_data in unit_data.chapters:
            chapter = _mapped_entity(db, "chapter", chapter_data.stable_id, Chapter, conflicts)
            if chapter is None and unit is not None:
                chapter = (
                    db.query(Chapter)
                    .filter(Chapter.unit_id == unit.id, Chapter.order == chapter_data.order)
                    .one_or_none()
                )
            chapter_values = {
                "unit_id": unit.id if unit is not None else None,
                "title_ar": chapter_data.title_ar,
                "order": chapter_data.order,
                "difficulty": 2,
            }
            _record_entity_change(chapter, chapter_values, counts)
            if chapter is not None:
                stable_mapping[chapter_data.stable_id] = chapter.id
            chapter_mapping = _mapping_for_stable_id(db, "chapter", chapter_data.stable_id)
            if chapter_mapping is None:
                counts.mappings_inserted += 1
            elif chapter is not None:
                values = _mapping_values(
                    version=version,
                    source_path=source_path,
                    metadata={"chapter_number": chapter_data.chapter_number, "title_ar": chapter_data.title_ar},
                )
                if chapter_mapping.entity_id != chapter.id or _different(chapter_mapping, values):
                    counts.mappings_updated += 1
                else:
                    counts.mappings_unchanged += 1

            for lesson_data in chapter_data.lessons:
                lesson = _mapped_entity(db, "lesson", lesson_data.stable_id, Lesson, conflicts)
                if lesson is None and chapter is not None:
                    lesson = (
                        db.query(Lesson)
                        .filter(Lesson.chapter_id == chapter.id, Lesson.order == lesson_data.order)
                        .one_or_none()
                    )
                lesson_values = {
                    "chapter_id": chapter.id if chapter is not None else None,
                    "title_ar": lesson_data.title_ar,
                    "content_ar": _content_ar(
                        lesson_data.printed_page_start,
                        lesson_data.printed_page_end,
                        [topic.title_ar for topic in lesson_data.topics],
                    ),
                    "order": lesson_data.order,
                    "difficulty": 2,
                    "duration_min": lesson_data.duration_min,
                    "page_start": lesson_data.printed_page_start,
                    "page_end": lesson_data.printed_page_end,
                }
                _record_entity_change(lesson, lesson_values, counts)
                if lesson is not None:
                    stable_mapping[lesson_data.stable_id] = lesson.id
                lesson_mapping = _mapping_for_stable_id(db, "lesson", lesson_data.stable_id)
                if lesson_mapping is None:
                    counts.mappings_inserted += 1
                elif lesson is not None:
                    values = _mapping_values(
                        version=version,
                        source_path=source_path,
                        metadata={
                            "unit_id": unit_data.stable_id,
                            "printed_page_start": lesson_data.printed_page_start,
                            "printed_page_end": lesson_data.printed_page_end,
                            "quality_status": lesson_data.quality_status,
                        },
                    )
                    if lesson_mapping.entity_id != lesson.id or _different(lesson_mapping, values):
                        counts.mappings_updated += 1
                    else:
                        counts.mappings_unchanged += 1

                for topic_data in lesson_data.topics:
                    topic = _mapped_entity(db, "topic", topic_data.stable_id, Topic, conflicts)
                    if topic is None:
                        matches = db.query(Topic).filter(Topic.title_ar == topic_data.title_ar).all()
                        if len(matches) > 1:
                            conflicts.append(
                                CurriculumImportConflict(
                                    code="AMBIGUOUS_TOPIC_TITLE",
                                    entity_type="topic",
                                    stable_id=topic_data.stable_id,
                                    message="More than one topic has the reviewed title.",
                                )
                            )
                        topic = matches[0] if len(matches) == 1 else None
                    topic_values = {
                        "title_ar": topic_data.title_ar,
                        "description_ar": (
                            f"صفحات الكتاب: {topic_data.page_start}-{topic_data.page_end}"
                        ),
                        "category": "reviewed_subtopic",
                        "difficulty": 1,
                        "order": topic_data.order,
                    }
                    _record_entity_change(topic, topic_values, counts)
                    if topic is not None:
                        stable_mapping[topic_data.stable_id] = topic.id
                    topic_mapping = _mapping_for_stable_id(db, "topic", topic_data.stable_id)
                    if topic_mapping is None:
                        counts.mappings_inserted += 1
                    elif topic is not None:
                        values = _mapping_values(
                            version=version,
                            source_path=source_path,
                            metadata={
                                "lesson_id": lesson_data.stable_id,
                                "page_start": topic_data.page_start,
                                "page_end": topic_data.page_end,
                                "quality_status": topic_data.quality_status,
                                "quality_score": topic_data.quality_score,
                            },
                        )
                        if topic_mapping.entity_id != topic.id or _different(topic_mapping, values):
                            counts.mappings_updated += 1
                        else:
                            counts.mappings_unchanged += 1

    counts.conflicting = len(conflicts)
    return counts, conflicts, stable_mapping


def _apply_catalog(
    db: Session,
    catalog: ReviewedCurriculumCatalog,
) -> tuple[CurriculumImportCounts, dict[str, int]]:
    counts = CurriculumImportCounts()
    stable_mapping: dict[str, int] = {}
    version = catalog.reviewed_metadata_version
    source_path = _relative(CANONICAL_CURRICULUM_PATH)

    for unit_data in catalog.units:
        unit = _mapping_for_stable_id(db, "unit", unit_data.stable_id)
        unit_row = db.get(Unit, unit.entity_id) if unit else None
        unit_row = unit_row or db.query(Unit).filter(Unit.unit_number == unit_data.unit_number).one_or_none()
        unit_values = {
            "unit_number": unit_data.unit_number,
            "semester": unit_data.semester,
            "title_ar": unit_data.title_ar,
            "order": unit_data.order,
        }
        _record_entity_change(unit_row, unit_values, counts)
        if unit_row is None:
            unit_row = Unit(**unit_values)
            db.add(unit_row)
        else:
            for field, value in unit_values.items():
                setattr(unit_row, field, value)
        db.flush()
        _upsert_mapping(
            db,
            entity_type="unit",
            stable_id=unit_data.stable_id,
            entity_id=unit_row.id,
            version=version,
            source_path=source_path,
            metadata={"unit_number": unit_data.unit_number, "title_ar": unit_data.title_ar},
            counts=counts,
            stable_mapping=stable_mapping,
        )

        for chapter_data in unit_data.chapters:
            chapter_mapping = _mapping_for_stable_id(db, "chapter", chapter_data.stable_id)
            chapter = db.get(Chapter, chapter_mapping.entity_id) if chapter_mapping else None
            chapter = chapter or (
                db.query(Chapter)
                .filter(Chapter.unit_id == unit_row.id, Chapter.order == chapter_data.order)
                .one_or_none()
            )
            chapter_values = {
                "unit_id": unit_row.id,
                "title_ar": chapter_data.title_ar,
                "order": chapter_data.order,
                "difficulty": 2,
            }
            _record_entity_change(chapter, chapter_values, counts)
            if chapter is None:
                chapter = Chapter(**chapter_values)
                db.add(chapter)
            else:
                for field, value in chapter_values.items():
                    setattr(chapter, field, value)
            db.flush()
            _upsert_mapping(
                db,
                entity_type="chapter",
                stable_id=chapter_data.stable_id,
                entity_id=chapter.id,
                version=version,
                source_path=source_path,
                metadata={"chapter_number": chapter_data.chapter_number, "title_ar": chapter_data.title_ar},
                counts=counts,
                stable_mapping=stable_mapping,
            )

            for lesson_data in chapter_data.lessons:
                lesson_mapping = _mapping_for_stable_id(db, "lesson", lesson_data.stable_id)
                lesson = db.get(Lesson, lesson_mapping.entity_id) if lesson_mapping else None
                lesson = lesson or (
                    db.query(Lesson)
                    .filter(Lesson.chapter_id == chapter.id, Lesson.order == lesson_data.order)
                    .one_or_none()
                )
                lesson_values = {
                    "chapter_id": chapter.id,
                    "title_ar": lesson_data.title_ar,
                    "content_ar": _content_ar(
                        lesson_data.printed_page_start,
                        lesson_data.printed_page_end,
                        [topic.title_ar for topic in lesson_data.topics],
                    ),
                    "order": lesson_data.order,
                    "difficulty": 2,
                    "duration_min": lesson_data.duration_min,
                    "page_start": lesson_data.printed_page_start,
                    "page_end": lesson_data.printed_page_end,
                }
                _record_entity_change(lesson, lesson_values, counts)
                if lesson is None:
                    lesson = Lesson(**lesson_values)
                    db.add(lesson)
                else:
                    for field, value in lesson_values.items():
                        setattr(lesson, field, value)
                db.flush()
                _upsert_mapping(
                    db,
                    entity_type="lesson",
                    stable_id=lesson_data.stable_id,
                    entity_id=lesson.id,
                    version=version,
                    source_path=source_path,
                    metadata={
                        "unit_id": unit_data.stable_id,
                        "printed_page_start": lesson_data.printed_page_start,
                        "printed_page_end": lesson_data.printed_page_end,
                        "quality_status": lesson_data.quality_status,
                    },
                    counts=counts,
                    stable_mapping=stable_mapping,
                )

                desired_topics: list[Topic] = []
                for topic_data in lesson_data.topics:
                    topic_mapping = _mapping_for_stable_id(db, "topic", topic_data.stable_id)
                    topic = db.get(Topic, topic_mapping.entity_id) if topic_mapping else None
                    topic = topic or db.query(Topic).filter(Topic.title_ar == topic_data.title_ar).one_or_none()
                    topic_values = {
                        "title_ar": topic_data.title_ar,
                        "description_ar": f"صفحات الكتاب: {topic_data.page_start}-{topic_data.page_end}",
                        "category": "reviewed_subtopic",
                        "difficulty": 1,
                        "order": topic_data.order,
                    }
                    _record_entity_change(topic, topic_values, counts)
                    if topic is None:
                        topic = Topic(**topic_values)
                        db.add(topic)
                    else:
                        for field, value in topic_values.items():
                            setattr(topic, field, value)
                    db.flush()
                    _upsert_mapping(
                        db,
                        entity_type="topic",
                        stable_id=topic_data.stable_id,
                        entity_id=topic.id,
                        version=version,
                        source_path=source_path,
                        metadata={
                            "lesson_id": lesson_data.stable_id,
                            "page_start": topic_data.page_start,
                            "page_end": topic_data.page_end,
                            "quality_status": topic_data.quality_status,
                            "quality_score": topic_data.quality_score,
                        },
                        counts=counts,
                        stable_mapping=stable_mapping,
                    )
                    desired_topics.append(topic)

                existing_topic_ids = {topic.id for topic in lesson.topics}
                for topic in desired_topics:
                    if topic.id not in existing_topic_ids:
                        lesson.topics.append(topic)

    return counts, stable_mapping


def import_reviewed_curriculum(
    db: Session,
    *,
    catalog: ReviewedCurriculumCatalog | None = None,
    catalog_path: Path = CANONICAL_CURRICULUM_PATH,
    dry_run: bool = True,
    allow_destructive: bool = False,
) -> CurriculumImportReport:
    """Plan or apply one canonical curriculum import.

    Existing rows are updated in place and no row is deleted. Destructive mode is
    deliberately unsupported until a separate maintenance workflow is reviewed.
    """

    if allow_destructive:
        raise CurriculumImportError("DESTRUCTIVE_CURRICULUM_IMPORT_NOT_IMPLEMENTED")
    started_at = datetime.now(timezone.utc)
    catalog = catalog or load_canonical_curriculum_catalog(catalog_path)
    counts, conflicts, stable_mapping = _inspect_catalog(db, catalog)
    if conflicts:
        return CurriculumImportReport(
            status="conflict",
            dry_run=dry_run,
            catalog_path=_relative(catalog_path),
            reviewed_metadata_version=catalog.reviewed_metadata_version,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            counts=counts,
            conflicts=conflicts,
            stable_id_mapping=stable_mapping,
        )
    if dry_run:
        return CurriculumImportReport(
            status="dry_run",
            dry_run=True,
            catalog_path=_relative(catalog_path),
            reviewed_metadata_version=catalog.reviewed_metadata_version,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            counts=counts,
            stable_id_mapping=stable_mapping,
        )

    try:
        applied_counts, applied_mapping = _apply_catalog(db, catalog)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return CurriculumImportReport(
        status="applied",
        dry_run=False,
        catalog_path=_relative(catalog_path),
        reviewed_metadata_version=catalog.reviewed_metadata_version,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        counts=applied_counts,
        stable_id_mapping=applied_mapping,
    )

