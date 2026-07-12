#!/usr/bin/env python3
"""Build the Ask AI Grade 9 gold questions from reviewed curriculum assets.

The output is deterministic and contains no model-generated expectations. Every
lesson, subtopic, page, and identifier comes from reviewed files under
``data/processed``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
SUBTOPICS_PATH = REPO_ROOT / "data" / "processed" / "textbook" / "textbook_subtopics.jsonl"
BOOK_STRUCTURE_PATH = REPO_ROOT / "data" / "processed" / "book_structure.json"
CHUNK_PREVIEW_PATH = (
    REPO_ROOT / "data" / "processed" / "chunk_preview" / "textbook_chunks_preview.jsonl"
)
REVIEWED_METADATA_PATH = (
    REPO_ROOT / "data" / "processed" / "curriculum" / "reviewed_curriculum_metadata.json"
)
OUTPUT_PATH = BACKEND_DIR / "tests" / "fixtures" / "ask_ai_grade9_book_questions.json"

ACID_WATER_CHUNK_ID = "chunk_unit_04_lesson_01_0084"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(row)
    return rows


def _lesson_ranges() -> dict[str, tuple[str, int, int]]:
    payload = json.loads(BOOK_STRUCTURE_PATH.read_text(encoding="utf-8"))
    ranges: dict[str, tuple[str, int, int]] = {}
    for unit in payload.get("units") or []:
        unit_id = str(unit.get("unit_id") or "")
        for lesson in unit.get("lessons") or []:
            lesson_id = str(lesson.get("lesson_id") or "")
            start = lesson.get("printed_page_start")
            end = lesson.get("printed_page_end")
            if lesson_id and unit_id and isinstance(start, int) and isinstance(end, int):
                ranges[lesson_id] = (unit_id, start, end)
    if not ranges:
        raise ValueError(f"No reviewed lesson ranges found in {BOOK_STRUCTURE_PATH}")
    return ranges


def _metadata_version() -> str:
    payload = json.loads(REVIEWED_METADATA_PATH.read_text(encoding="utf-8"))
    version = str(payload.get("version") or "").strip()
    if not version:
        raise ValueError(f"Reviewed metadata version is missing in {REVIEWED_METADATA_PATH}")
    return version


def _subtopic_case(
    row: dict[str, Any],
    *,
    lesson_ranges: dict[str, tuple[str, int, int]],
    metadata_version: str,
) -> dict[str, Any]:
    required = (
        "subtopic_id",
        "unit_id",
        "lesson_id",
        "lesson_title",
        "subtopic_title",
        "page_start",
        "page_end",
    )
    missing = [field for field in required if row.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Reviewed subtopic {row.get('subtopic_id')} is missing {missing}")

    lesson_id = str(row["lesson_id"])
    unit_id = str(row["unit_id"])
    page_start = int(row["page_start"])
    page_end = int(row["page_end"])
    lesson_range = lesson_ranges.get(lesson_id)
    if lesson_range is None:
        raise ValueError(f"Subtopic {row['subtopic_id']} references unknown lesson {lesson_id}")
    expected_unit_id, lesson_start, lesson_end = lesson_range
    if unit_id != expected_unit_id:
        raise ValueError(
            f"Subtopic {row['subtopic_id']} unit {unit_id} disagrees with lesson unit {expected_unit_id}"
        )
    if page_start > page_end or page_start < lesson_start or page_end > lesson_end:
        raise ValueError(
            f"Subtopic {row['subtopic_id']} pages {page_start}-{page_end} fall outside "
            f"lesson range {lesson_start}-{lesson_end}"
        )

    title = str(row["subtopic_title"]).strip()
    evidence = row.get("evidence") if isinstance(row.get("evidence"), list) else []
    return {
        "id": str(row["subtopic_id"]),
        "question_ar": f"ما المقصود بـ «{title}»؟",
        "paraphrases_ar": [
            f"اشرح «{title}» كما ورد في كتاب الكيمياء.",
            f"وضّح لي مفهوم «{title}».",
        ],
        "expected_concepts": [title],
        "expected_unit_id": unit_id,
        "expected_lesson_id": lesson_id,
        "expected_printed_pages": list(range(page_start, page_end + 1)),
        "expected_source_type": "textbook",
        "answerable_from_book": True,
        "lesson_title": str(row["lesson_title"]),
        "source_subtopic_id": str(row["subtopic_id"]),
        "source_evidence": evidence,
        "reviewed_metadata_version": metadata_version,
    }


def _acid_water_case(*, metadata_version: str) -> dict[str, Any]:
    chunks = _read_jsonl(CHUNK_PREVIEW_PATH)
    evidence = next((item for item in chunks if item.get("chunk_id") == ACID_WATER_CHUNK_ID), None)
    if evidence is None:
        raise ValueError(f"Reviewed acid/water evidence chunk {ACID_WATER_CHUNK_ID} was not found")
    if evidence.get("blocked") is True or evidence.get("quality_status") != "ready":
        raise ValueError(f"Reviewed acid/water evidence chunk {ACID_WATER_CHUNK_ID} is not ready")
    content = str(evidence.get("content") or "")
    if "أضف الحمض إلى الماء" not in content:
        raise ValueError(f"Reviewed acid/water evidence text is missing in {ACID_WATER_CHUNK_ID}")

    return {
        "id": "unit_04_lesson_01_safety_acid_into_water",
        "question_ar": "لماذا نضيف الحمض إلى الماء وليس العكس؟",
        "paraphrases_ar": [
            "ما قاعدة الأمان عند خلط الحمض بالماء؟",
            "هل نضيف الماء إلى الحمض أم الحمض إلى الماء؟",
        ],
        "expected_concepts": ["أضف الحمض إلى الماء"],
        "expected_unit_id": "unit_04",
        "expected_lesson_id": "unit_04_lesson_01",
        "expected_printed_pages": [113],
        "expected_source_type": "textbook",
        "answerable_from_book": True,
        "lesson_title": "المحاليل المائية",
        "source_subtopic_id": None,
        "source_evidence": [ACID_WATER_CHUNK_ID],
        "reviewed_metadata_version": metadata_version,
    }


def build_cases() -> list[dict[str, Any]]:
    lesson_ranges = _lesson_ranges()
    metadata_version = _metadata_version()
    subtopics = _read_jsonl(SUBTOPICS_PATH)
    cases = [
        _subtopic_case(row, lesson_ranges=lesson_ranges, metadata_version=metadata_version)
        for row in subtopics
    ]
    cases.append(_acid_water_case(metadata_version=metadata_version))

    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Ask AI question ids must be unique")
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--check", action="store_true", help="Fail when the existing output is stale.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rendered = json.dumps(build_cases(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(f"Ask AI gold dataset is stale: {args.output}")
            return 1
        print(f"Ask AI gold dataset is current: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {len(json.loads(rendered))} reviewed Ask AI cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
