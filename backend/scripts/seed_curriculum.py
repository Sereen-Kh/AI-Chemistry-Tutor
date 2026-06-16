"""Seed the chemistry curriculum from the nested book_structure.json catalog."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: F401,E402
from app.models.chemistry import Chapter, Lesson, Unit  # noqa: E402
from app.models.textbook import ContentSource, RagChunk  # noqa: E402
from app.models.topic import Topic  # noqa: E402


LEGACY_FLAT_CHAPTER_TITLES = {
    "الكيمياء اللاعضوية والكيمياء العضوية",
    "الكيمياء اللاعضوية",
}


def _page_range(pages: list[int] | None) -> tuple[int | None, int | None]:
    if not pages:
        return None, None
    normalized = [int(page) for page in pages]
    start = normalized[0]
    end = normalized[-1]
    if start > end:
        raise ValueError(f"Invalid descending page range: {pages}")
    return start, end


def _objectives_content(objectives: list[str], page_start: int | None, page_end: int | None) -> str:
    lines: list[str] = []
    if page_start is not None:
        page_label = f"{page_start}" if page_start == page_end else f"{page_start}-{page_end}"
        lines.append(f"صفحات الكتاب: {page_label}")
    if objectives:
        lines.append("الأهداف:")
        lines.extend(f"- {objective}" for objective in objectives)
    return "\n".join(lines)


def _find_content_source(db, source_slug: str, title_ar: str) -> ContentSource | None:
    candidates = db.query(ContentSource).filter(ContentSource.source_type == "textbook").all()
    for source in candidates:
        metadata = source.metadata_json if isinstance(source.metadata_json, dict) else {}
        if metadata.get("source_slug") == source_slug or source.title in {source_slug, title_ar}:
            return source
    return None


def _upsert_content_source(db, structure: dict[str, Any], stats: dict[str, int]) -> ContentSource:
    source_slug = structure.get("source_slug") or "syria_grade_9_chemistry"
    title_ar = structure.get("title_ar") or "كتاب الكيمياء - الصف التاسع"
    source = _find_content_source(db, source_slug, title_ar)
    metadata = dict(source.metadata_json or {}) if source else {}
    metadata.update({"source_slug": source_slug})
    if source is None:
        source = ContentSource(
            source_type="textbook",
            title=title_ar,
            grade="grade_9",
            subject="chemistry",
            status="ready",
            metadata_json=metadata,
        )
        db.add(source)
        stats["created"] += 1
        print(f"Created source: {source_slug}")
    else:
        source.title = title_ar
        source.metadata_json = metadata
        source.status = source.status or "ready"
        stats["updated"] += 1
        print(f"Updated source: {source_slug}")
    return source


def _upsert_unit(db, data: dict[str, Any], stats: dict[str, int]) -> Unit:
    unit_number = int(data["unit_number"])
    unit = db.query(Unit).filter(Unit.unit_number == unit_number).first()
    values = {
        "semester": int(data["semester"]),
        "title_ar": data["title_ar"],
        "title_en": data.get("title_en"),
        "description_ar": data.get("description_ar"),
        "order": int(data.get("order") or unit_number),
        "icon": data.get("icon"),
    }
    if unit is None:
        unit = Unit(unit_number=unit_number, **values)
        db.add(unit)
        stats["created"] += 1
        print(f"Created Unit {unit_number}: {unit.title_ar}")
    else:
        for field, value in values.items():
            setattr(unit, field, value)
        stats["updated"] += 1
        print(f"Updated Unit {unit_number}: {unit.title_ar}")
    db.flush()
    return unit


def _find_legacy_chapter(db, unit: Unit, data: dict[str, Any]) -> Chapter | None:
    if unit.unit_number != 4 or int(data.get("chapter_no") or 1) != 1:
        return None
    fallback_titles = LEGACY_FLAT_CHAPTER_TITLES | {data["title_ar"], unit.title_ar}
    return (
        db.query(Chapter)
        .filter(Chapter.unit_id.is_(None), Chapter.title_ar.in_(fallback_titles))
        .order_by(Chapter.id)
        .first()
    )


def _upsert_chapter(db, unit: Unit, data: dict[str, Any], stats: dict[str, int]) -> Chapter:
    order = int(data.get("order") or data.get("chapter_no") or 0)
    chapter = db.query(Chapter).filter(Chapter.unit_id == unit.id, Chapter.order == order).first()
    if chapter is None:
        chapter = _find_legacy_chapter(db, unit, data)

    values = {
        "unit_id": unit.id,
        "title_ar": data["title_ar"],
        "title_en": data.get("title_en"),
        "description_ar": data.get("description_ar"),
        "order": order,
        "difficulty": int(data.get("difficulty") or 2),
        "icon": data.get("icon") or unit.icon,
    }
    if chapter is None:
        chapter = Chapter(**values)
        db.add(chapter)
        stats["created"] += 1
        print(f"Created Chapter {order}: {chapter.title_ar}")
    else:
        for field, value in values.items():
            setattr(chapter, field, value)
        stats["updated"] += 1
        print(f"Updated Chapter {order}: {chapter.title_ar}")
    db.flush()
    updated_chunks = (
        db.query(RagChunk)
        .filter(RagChunk.chapter_id == chapter.id, RagChunk.unit_id.is_(None))
        .update({RagChunk.unit_id: unit.id}, synchronize_session=False)
    )
    if updated_chunks:
        print(f"Backfilled unit_id={unit.id} on {updated_chunks} RAG chunks for Chapter {chapter.id}")
    return chapter


def _upsert_lesson(db, chapter: Chapter, data: dict[str, Any], stats: dict[str, int]) -> Lesson:
    order = int(data.get("lesson_no") or data.get("order") or 0)
    page_start, page_end = _page_range(data.get("book_pages") or [])
    content_ar = _objectives_content(data.get("objectives") or [], page_start, page_end)
    lesson = db.query(Lesson).filter(Lesson.chapter_id == chapter.id, Lesson.order == order).first()
    if lesson is None:
        lesson = db.query(Lesson).filter(Lesson.chapter_id == chapter.id, Lesson.title_ar == data["title_ar"]).first()

    values = {
        "chapter_id": chapter.id,
        "title_ar": data["title_ar"],
        "title_en": data.get("title_en"),
        "content_ar": content_ar,
        "order": order,
        "difficulty": int(data.get("difficulty") or 2),
        "duration_min": int(data.get("duration_minutes") or data.get("duration_min") or 45),
        "page_start": page_start,
        "page_end": page_end,
    }
    if lesson is None:
        lesson = Lesson(**values)
        db.add(lesson)
        stats["created"] += 1
        print(f"Created Lesson {order}: {lesson.title_ar}")
    else:
        for field, value in values.items():
            setattr(lesson, field, value)
        stats["updated"] += 1
        print(f"Updated Lesson {order}: {lesson.title_ar}")
    db.flush()
    return lesson


def _upsert_topic(db, data: dict[str, Any], stats: dict[str, int]) -> Topic:
    title_ar = data["title_ar"]
    topic = db.query(Topic).filter(Topic.title_ar == title_ar).first()
    values = {
        "title_en": data.get("title_en"),
        "description_ar": data.get("description_ar"),
        "category": data.get("category"),
        "difficulty": int(data.get("difficulty") or 1),
        "icon": data.get("icon"),
        "order": int(data.get("order") or 0),
    }
    if topic is None:
        topic = Topic(title_ar=title_ar, **values)
        db.add(topic)
        stats["created"] += 1
        print(f"Created Topic: {title_ar}")
    else:
        for field, value in values.items():
            if value is not None:
                setattr(topic, field, value)
        stats["updated"] += 1
        print(f"Updated Topic: {title_ar}")
    db.flush()
    return topic


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    stats = {"created": 0, "updated": 0, "skipped": 0}
    try:
        book_structure_path = PROJECT_DIR / "data" / "textbooks" / "syria_grade_9_chemistry" / "book_structure.json"
        if not book_structure_path.exists():
            print(f"Error: book_structure.json not found at {book_structure_path}")
            sys.exit(1)

        structure = json.loads(book_structure_path.read_text(encoding="utf-8"))
        _upsert_content_source(db, structure, stats)

        for unit_data in structure.get("units") or []:
            unit = _upsert_unit(db, unit_data, stats)
            for chapter_data in unit_data.get("chapters") or []:
                chapter = _upsert_chapter(db, unit, chapter_data, stats)
                for lesson_data in chapter_data.get("lessons") or []:
                    lesson = _upsert_lesson(db, chapter, lesson_data, stats)
                    for topic_data in lesson_data.get("topics") or []:
                        topic = _upsert_topic(db, topic_data, stats)
                        if topic not in lesson.topics:
                            lesson.topics.append(topic)
                            stats["created"] += 1
                            print(f"Linked Lesson {lesson.id} -> Topic {topic.id}")
                        else:
                            stats["skipped"] += 1

        db.commit()
        print(
            "Curriculum seeding completed: "
            f"created={stats['created']} updated={stats['updated']} skipped={stats['skipped']}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
