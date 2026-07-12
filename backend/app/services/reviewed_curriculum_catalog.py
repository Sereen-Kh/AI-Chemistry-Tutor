"""Build the canonical DB curriculum catalog from reviewed extraction assets."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from app.schemas.curriculum_catalog import ReviewedCurriculumCatalog
from app.services.curriculum_readiness import REPO_ROOT
from app.services.reviewed_curriculum_metadata import load_reviewed_curriculum_metadata


REVIEWED_STRUCTURE_PATH = REPO_ROOT / "data/processed/book_structure.json"
REVIEWED_SUBTOPICS_PATH = REPO_ROOT / "data/processed/textbook/textbook_subtopics.jsonl"
LEGACY_NESTED_STRUCTURE_PATH = (
    REPO_ROOT / "src/data/textbooks/syria_grade_9_chemistry/book_structure.json"
)
CANONICAL_CURRICULUM_PATH = (
    REPO_ROOT / "data/processed/curriculum/grade_9_chemistry_curriculum.reviewed.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object at {path}:{line_number}")
        rows.append(row)
    return rows


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _quality_status(score: float) -> str:
    return "ready" if score >= 0.85 else "needs_review"


def build_reviewed_curriculum_catalog(
    *,
    reviewed_structure: dict[str, Any] | None = None,
    subtopics: list[dict[str, Any]] | None = None,
    nested_structure: dict[str, Any] | None = None,
    reviewed_metadata: dict[str, Any] | None = None,
) -> ReviewedCurriculumCatalog:
    """Merge reviewed ranges/subtopics with chapter labels from the legacy catalog.

    Lesson titles, page ranges, and topics always come from reviewed outputs. The
    legacy nested structure contributes only semester and chapter presentation data.
    """

    reviewed_structure = reviewed_structure or _read_json(REVIEWED_STRUCTURE_PATH)
    subtopics = subtopics or _read_jsonl(REVIEWED_SUBTOPICS_PATH)
    nested_structure = nested_structure or _read_json(LEGACY_NESTED_STRUCTURE_PATH)
    reviewed_metadata = reviewed_metadata or load_reviewed_curriculum_metadata(require_ready=False)

    if reviewed_metadata.get("status") != "reviewed" or not reviewed_metadata.get("version"):
        raise ValueError("Reviewed curriculum metadata must have reviewed status and a version")

    nested_by_unit = {
        int(unit["unit_number"]): unit
        for unit in nested_structure.get("units") or []
        if isinstance(unit, dict) and unit.get("unit_number") is not None
    }
    subtopics_by_lesson: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in subtopics:
        lesson_id = str(row.get("lesson_id") or "")
        if not lesson_id:
            raise ValueError("Reviewed subtopic is missing lesson_id")
        subtopics_by_lesson[lesson_id].append(row)

    units: list[dict[str, Any]] = []
    expected_lesson_ids: set[str] = set()
    for reviewed_unit in reviewed_structure.get("units") or []:
        unit_number = int(reviewed_unit["unit_number"])
        stable_unit_id = str(reviewed_unit["unit_id"])
        nested_unit = nested_by_unit.get(unit_number)
        if nested_unit is None:
            raise ValueError(f"No chapter metadata for reviewed unit {stable_unit_id}")
        nested_chapters = [row for row in nested_unit.get("chapters") or [] if isinstance(row, dict)]
        if len(nested_chapters) != 1:
            raise ValueError(f"Expected exactly one reviewed chapter shell for {stable_unit_id}")
        nested_chapter = nested_chapters[0]
        chapter_number = int(nested_chapter.get("chapter_no") or nested_chapter.get("order") or 1)
        lessons: list[dict[str, Any]] = []

        for reviewed_lesson in reviewed_unit.get("lessons") or []:
            stable_lesson_id = str(reviewed_lesson["lesson_id"])
            expected_lesson_ids.add(stable_lesson_id)
            lesson_topics = sorted(
                subtopics_by_lesson.get(stable_lesson_id, []),
                key=lambda row: (int(row.get("page_start") or 0), str(row.get("subtopic_id") or "")),
            )
            if not lesson_topics:
                raise ValueError(f"Reviewed lesson {stable_lesson_id} has no reviewed subtopics")

            lesson_start = int(reviewed_lesson["printed_page_start"])
            lesson_end = int(reviewed_lesson["printed_page_end"])
            topics: list[dict[str, Any]] = []
            for order, topic in enumerate(lesson_topics, start=1):
                page_start = int(topic["page_start"])
                page_end = int(topic["page_end"])
                if page_start < lesson_start or page_end > lesson_end:
                    raise ValueError(
                        f"Subtopic {topic.get('subtopic_id')} range {page_start}-{page_end} "
                        f"falls outside lesson {stable_lesson_id} range {lesson_start}-{lesson_end}"
                    )
                quality_score = float(topic.get("quality_score") or 0.0)
                topics.append(
                    {
                        "stable_id": str(topic["subtopic_id"]),
                        "title_ar": str(topic["subtopic_title"]).strip(),
                        "order": order,
                        "page_start": page_start,
                        "page_end": page_end,
                        "quality_status": _quality_status(quality_score),
                        "quality_score": quality_score,
                    }
                )

            lessons.append(
                {
                    "stable_id": stable_lesson_id,
                    "lesson_number": int(reviewed_lesson["lesson_number"]),
                    "title_ar": str(reviewed_lesson["lesson_title"]).strip(),
                    "order": int(reviewed_lesson["lesson_number"]),
                    "printed_page_start": lesson_start,
                    "printed_page_end": lesson_end,
                    "pdf_page_start": reviewed_lesson.get("pdf_page_start"),
                    "pdf_page_end": reviewed_lesson.get("pdf_page_end"),
                    "quality_status": str(reviewed_lesson.get("quality", {}).get("status") or "needs_review"),
                    "quality_score": float(reviewed_lesson.get("quality", {}).get("score") or 0.0),
                    "duration_min": 45,
                    "topics": topics,
                }
            )

        units.append(
            {
                "stable_id": stable_unit_id,
                "unit_number": unit_number,
                "semester": int(nested_unit.get("semester") or 1),
                "title_ar": str(reviewed_unit["unit_title"]).strip(),
                "order": unit_number,
                "chapters": [
                    {
                        "stable_id": f"{stable_unit_id}_chapter_{chapter_number:02d}",
                        "chapter_number": chapter_number,
                        "title_ar": str(nested_chapter["title_ar"]).strip(),
                        "order": int(nested_chapter.get("order") or chapter_number),
                        "lessons": lessons,
                    }
                ],
            }
        )

    unexpected = sorted(set(subtopics_by_lesson) - expected_lesson_ids)
    if unexpected:
        raise ValueError(f"Reviewed subtopics reference unknown lessons: {', '.join(unexpected)}")

    return ReviewedCurriculumCatalog.model_validate(
        {
            "reviewed_metadata_version": str(reviewed_metadata["version"]),
            "generated_at": datetime.now(timezone.utc),
            "source_paths": [
                _relative(REVIEWED_STRUCTURE_PATH),
                _relative(REVIEWED_SUBTOPICS_PATH),
                _relative(LEGACY_NESTED_STRUCTURE_PATH),
            ],
            "units": units,
        }
    )


def write_reviewed_curriculum_catalog(
    catalog: ReviewedCurriculumCatalog | None = None,
    *,
    output_path: Path = CANONICAL_CURRICULUM_PATH,
) -> Path:
    payload = catalog or build_reviewed_curriculum_catalog()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path

