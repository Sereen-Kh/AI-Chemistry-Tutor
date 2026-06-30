"""Validate reviewed textbook book structure metadata.

Run from ``src/backend``:

    python -m app.scripts.validate_book_structure
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parents[1]

BOOK_STRUCTURE_PATH = REPO_ROOT / "data/processed/book_structure.json"
REVIEWED_LESSON_MAP_PATH = (
    REPO_ROOT / "data/processed/textbook/textbook_lesson_map.reviewed.json"
)
SOURCE_BOOK_STRUCTURE_PATH = (
    REPO_ROOT / "src/data/textbooks/syria_grade_9_chemistry/book_structure.json"
)
REPORT_DIR = REPO_ROOT / "reports/book_structure_update"
VALIDATION_JSON_PATH = REPORT_DIR / "book_structure_validation_report.json"
VALIDATION_MD_PATH = REPORT_DIR / "book_structure_validation_report.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _quality_status(item: dict[str, Any]) -> str:
    return str((item.get("quality") or {}).get("status") or item.get("quality_status") or "")


def _quality_list(item: dict[str, Any], key: str) -> list[Any]:
    quality = item.get("quality") or {}
    value = quality.get(key, item.get(key, []))
    return list(value or [])


def _lesson_label(unit: dict[str, Any], lesson: dict[str, Any]) -> str:
    return f"{unit.get('unit_id') or 'unknown_unit'}:{lesson.get('lesson_id') or lesson.get('lesson_title') or 'unknown_lesson'}"


def _source_units_up_to_four() -> set[int]:
    if not SOURCE_BOOK_STRUCTURE_PATH.exists():
        return set()
    payload = _load_json(SOURCE_BOOK_STRUCTURE_PATH)
    unit_numbers: set[int] = set()
    for unit in payload.get("units", []):
        try:
            unit_number = int(unit.get("unit_number"))
        except (TypeError, ValueError):
            continue
        if unit_number <= 4:
            unit_numbers.add(unit_number)
    return unit_numbers


def validate() -> dict[str, Any]:
    remaining_issues: list[str] = []
    lessons_with_missing_ids: list[str] = []
    lessons_with_missing_page_ranges: list[str] = []
    overlapping_ranges: list[dict[str, Any]] = []
    ready_lessons_with_blockers: list[str] = []
    unordered_lessons: list[str] = []
    units_with_missing_ids: list[int | str] = []

    book_structure_exists = BOOK_STRUCTURE_PATH.exists()
    reviewed_lesson_map_exists = REVIEWED_LESSON_MAP_PATH.exists()
    book_structure = _load_json(BOOK_STRUCTURE_PATH) if book_structure_exists else {}
    units = list(book_structure.get("units") or [])
    unit_by_number = {unit.get("unit_number"): unit for unit in units}
    unit_5 = unit_by_number.get(5)
    unit_6 = unit_by_number.get(6)
    unit_5_lessons = list((unit_5 or {}).get("lessons") or [])
    unit_6_lessons = list((unit_6 or {}).get("lessons") or [])

    for unit in units:
        unit_number = unit.get("unit_number", "unknown")
        if not unit.get("unit_id"):
            units_with_missing_ids.append(unit_number)

        lessons = list(unit.get("lessons") or [])
        previous_end: int | None = None
        previous_label: str | None = None
        previous_start: int | None = None

        for lesson in lessons:
            label = _lesson_label(unit, lesson)
            start = lesson.get("printed_page_start")
            end = lesson.get("printed_page_end")
            status = _quality_status(lesson)

            if not lesson.get("lesson_id"):
                lessons_with_missing_ids.append(label)

            if start is None or (end is None and status != "needs_review"):
                lessons_with_missing_page_ranges.append(label)

            if 190 in _quality_list(lesson, "needs_ocr_pages"):
                remaining_issues.append(f"{label} still lists page 190 in needs_ocr_pages")

            if 190 in _quality_list(lesson, "needs_vision_pages"):
                remaining_issues.append(f"{label} still lists page 190 in needs_vision_pages")

            blocked_pages = _quality_list(lesson, "blocked_pages")
            if status == "ready" and blocked_pages:
                ready_lessons_with_blockers.append(label)

            if isinstance(start, int) and isinstance(end, int):
                if previous_start is not None and start < previous_start:
                    unordered_lessons.append(label)
                if previous_end is not None and start <= previous_end:
                    overlapping_ranges.append(
                        {
                            "unit_id": unit.get("unit_id"),
                            "previous_lesson": previous_label,
                            "current_lesson": label,
                            "previous_end": previous_end,
                            "current_start": start,
                        }
                    )
                previous_start = start
                previous_end = end
                previous_label = label

    unit_6_page_190_ready = any(
        lesson.get("lesson_id") == "unit_06_lesson_01"
        and lesson.get("printed_page_start") == 190
        and _quality_status(lesson) == "ready"
        and 190 not in _quality_list(lesson, "needs_ocr_pages")
        and 190 not in _quality_list(lesson, "needs_vision_pages")
        and not _quality_list(lesson, "blocked_pages")
        for lesson in unit_6_lessons
    )

    source_units_up_to_four = _source_units_up_to_four()
    processed_units = {
        int(unit.get("unit_number"))
        for unit in units
        if isinstance(unit.get("unit_number"), int)
    }
    missing_previous_units = sorted(source_units_up_to_four - processed_units)

    checks = {
        "book_structure_exists": book_structure_exists,
        "reviewed_lesson_map_exists": reviewed_lesson_map_exists,
        "unit_5_exists": unit_5 is not None,
        "unit_6_exists": unit_6 is not None,
        "unit_5_has_lessons": len(unit_5_lessons) > 0,
        "unit_6_has_lessons": len(unit_6_lessons) > 0,
        "unit_6_page_190_ready": unit_6_page_190_ready,
        "all_units_have_ids": not units_with_missing_ids,
        "all_lessons_have_ids": not lessons_with_missing_ids,
        "all_lessons_have_required_ranges": not lessons_with_missing_page_ranges,
        "page_190_not_in_ocr_issues": not any(
            "needs_ocr_pages" in issue for issue in remaining_issues
        ),
        "page_190_not_in_vision_issues": not any(
            "needs_vision_pages" in issue for issue in remaining_issues
        ),
        "ready_lessons_have_no_blockers": not ready_lessons_with_blockers,
        "no_overlapping_ranges": not overlapping_ranges,
        "lesson_ordering_correct": not unordered_lessons,
        "previous_units_not_removed": not missing_previous_units,
    }

    for name, passed in checks.items():
        if not passed:
            remaining_issues.append(name)

    report = {
        "validation_status": "passed" if not remaining_issues else "failed",
        "unit_5_exists": checks["unit_5_exists"],
        "unit_6_exists": checks["unit_6_exists"],
        "unit_6_page_190_ready": unit_6_page_190_ready,
        "lessons_with_missing_ids": lessons_with_missing_ids,
        "lessons_with_missing_page_ranges": lessons_with_missing_page_ranges,
        "overlapping_ranges": overlapping_ranges,
        "ready_lessons_with_blockers": ready_lessons_with_blockers,
        "remaining_issues": remaining_issues,
        "checks": checks,
        "units_with_missing_ids": units_with_missing_ids,
        "unordered_lessons": unordered_lessons,
        "missing_previous_units": missing_previous_units,
        "unit_counts": {
            "total_units": len(units),
            "unit_5_lessons": len(unit_5_lessons),
            "unit_6_lessons": len(unit_6_lessons),
        },
        "files_checked": {
            "book_structure": str(BOOK_STRUCTURE_PATH.relative_to(REPO_ROOT)),
            "reviewed_lesson_map": str(
                REVIEWED_LESSON_MAP_PATH.relative_to(REPO_ROOT)
            ),
            "source_book_structure": str(
                SOURCE_BOOK_STRUCTURE_PATH.relative_to(REPO_ROOT)
            ),
        },
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    checks_md = "\n".join(
        f"- {name}: {'passed' if passed else 'failed'}"
        for name, passed in report["checks"].items()
    )
    md = f"""# Book Structure Validation Report

Validation status: `{report["validation_status"]}`

| Field | Value |
| --- | --- |
| Unit 5 exists | {report["unit_5_exists"]} |
| Unit 6 exists | {report["unit_6_exists"]} |
| Unit 6 page 190 ready | {report["unit_6_page_190_ready"]} |
| Unit 5 lessons | {report["unit_counts"]["unit_5_lessons"]} |
| Unit 6 lessons | {report["unit_counts"]["unit_6_lessons"]} |

## Checks

{checks_md}

## Remaining Issues

{json.dumps(report["remaining_issues"], ensure_ascii=False)}
"""
    VALIDATION_MD_PATH.write_text(md, encoding="utf-8")


def main() -> None:
    report = validate()
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["validation_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
