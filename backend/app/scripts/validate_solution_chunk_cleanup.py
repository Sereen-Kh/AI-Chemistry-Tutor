"""Validate cleaned solution-book chunks.

Run from ``src/backend``:

    python -m app.scripts.validate_solution_chunk_cleanup
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.scripts.cleanup_solution_chunks import (
    INPUT_UNITS,
    OUTPUT_CHUNKS,
    OUTPUT_PREVIEW,
    REPORT_DIR,
    REPO_ROOT,
    is_bad_chunk_ending,
)


VALIDATION_JSON = REPORT_DIR / "solution_chunk_validation_report.json"
VALIDATION_MD = REPORT_DIR / "solution_chunk_validation_report.md"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _unit_lesson_index() -> dict[str, str | None]:
    index: dict[str, str | None] = {}
    for unit in _read_jsonl(INPUT_UNITS):
        if unit.get("id"):
            index[str(unit["id"])] = unit.get("linked_textbook_lesson_id")
    return index


def validate() -> dict[str, Any]:
    cleaned_chunks_exists = OUTPUT_CHUNKS.exists()
    cleaned_preview_exists = OUTPUT_PREVIEW.exists()
    chunks = _read_jsonl(OUTPUT_CHUNKS)
    unit_lesson = _unit_lesson_index()

    bad_endings: list[dict[str, Any]] = []
    manual_review_bad_endings: list[dict[str, Any]] = []
    missing_metadata: list[dict[str, Any]] = []
    duplicate_hashes: list[dict[str, Any]] = []
    blocked_marked_ready: list[str] = []
    mixed_lessons: list[dict[str, Any]] = []
    empty_content: list[str] = []
    invalid_source_type: list[str] = []
    remaining_issues: list[str] = []

    hash_to_chunks: dict[str, list[str]] = defaultdict(list)
    required_fields = [
        "chunk_id",
        "source_type",
        "solution_unit_id",
        "content",
        "printed_page_start",
        "printed_page_end",
        "quality_status",
    ]

    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id") or "")
        content = str(chunk.get("content") or "")
        metadata = chunk.get("metadata") or {}
        quality_status = chunk.get("quality_status")

        if chunk.get("source_type") != "solution_book":
            invalid_source_type.append(chunk_id)

        missing = [
            field
            for field in required_fields
            if chunk.get(field) in (None, "", [])
        ]
        if not (chunk.get("lesson_id") or chunk.get("linked_textbook_lesson_id")):
            missing.append("lesson_id_or_linked_textbook_lesson_id")
        if not chunk.get("linked_textbook_lesson_id"):
            missing.append("linked_textbook_lesson_id")
        if not metadata.get("content_hash"):
            missing.append("metadata.content_hash")
        if missing:
            missing_metadata.append({"chunk_id": chunk_id, "missing": sorted(set(missing))})

        if not content.strip():
            empty_content.append(chunk_id)

        bad, reasons = is_bad_chunk_ending(content)
        if bad:
            item = {
                "chunk_id": chunk_id,
                "quality_status": quality_status,
                "reasons": reasons,
                "manual_review_reasons": metadata.get("manual_review_reasons") or [],
            }
            if quality_status == "needs_review" and metadata.get("manual_review_reasons"):
                manual_review_bad_endings.append(item)
            else:
                bad_endings.append(item)

        if quality_status == "ready" and (
            metadata.get("needs_manual_review") or metadata.get("manual_review_reasons")
        ):
            blocked_marked_ready.append(chunk_id)
        if quality_status == "ready" and "source_unit_blocked" in (
            metadata.get("manual_review_reasons") or []
        ):
            blocked_marked_ready.append(chunk_id)

        content_hash = metadata.get("content_hash")
        if content_hash:
            hash_to_chunks[str(content_hash)].append(chunk_id)

        source_unit_ids = metadata.get("solution_unit_ids") or [chunk.get("solution_unit_id")]
        lessons = {
            unit_lesson.get(str(source_unit_id))
            for source_unit_id in source_unit_ids
            if source_unit_id
        }
        lessons.discard(None)
        if len(lessons) > 1:
            mixed_lessons.append(
                {
                    "chunk_id": chunk_id,
                    "source_unit_ids": source_unit_ids,
                    "lessons": sorted(lessons),
                }
            )

    duplicate_hashes = [
        {"content_hash": content_hash, "chunk_ids": chunk_ids}
        for content_hash, chunk_ids in sorted(hash_to_chunks.items())
        if len(chunk_ids) > 1
    ]

    checks = {
        "cleaned_chunks_exists": cleaned_chunks_exists,
        "cleaned_preview_exists": cleaned_preview_exists,
        "has_chunks": len(chunks) > 0,
        "all_source_types_solution_book": not invalid_source_type,
        "all_required_metadata_present": not missing_metadata,
        "all_non_manual_review_chunks_end_cleanly": not bad_endings,
        "no_blocked_chunk_marked_ready": not blocked_marked_ready,
        "no_mixed_lessons": not mixed_lessons,
        "no_empty_content": not empty_content,
        "no_duplicate_content_hashes": not duplicate_hashes,
    }
    for name, passed in checks.items():
        if not passed:
            remaining_issues.append(name)

    report = {
        "validation_status": "passed" if not remaining_issues else "failed",
        "cleaned_chunks_exists": cleaned_chunks_exists,
        "cleaned_preview_exists": cleaned_preview_exists,
        "total_chunks": len(chunks),
        "bad_endings": bad_endings,
        "manual_review_bad_endings": manual_review_bad_endings,
        "missing_metadata": missing_metadata,
        "duplicate_hashes": duplicate_hashes,
        "blocked_marked_ready": blocked_marked_ready,
        "mixed_lessons": mixed_lessons,
        "empty_content": empty_content,
        "invalid_source_type": invalid_source_type,
        "remaining_issues": remaining_issues,
        "checks": checks,
        "files_checked": {
            "cleaned_chunks": str(OUTPUT_CHUNKS.relative_to(REPO_ROOT)),
            "cleaned_preview": str(OUTPUT_PREVIEW.relative_to(REPO_ROOT)),
            "input_solution_units": str(INPUT_UNITS.relative_to(REPO_ROOT)),
        },
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checks_md = "\n".join(
        f"- {name}: {'passed' if passed else 'failed'}"
        for name, passed in report["checks"].items()
    )
    md = f"""# Solution Chunk Validation Report

Validation status: `{report["validation_status"]}`

| Field | Value |
| --- | --- |
| Cleaned chunks exists | {report["cleaned_chunks_exists"]} |
| Cleaned preview exists | {report["cleaned_preview_exists"]} |
| Total chunks | {report["total_chunks"]} |
| Bad endings requiring failure | {len(report["bad_endings"])} |
| Manual-review bad endings allowed | {len(report["manual_review_bad_endings"])} |
| Missing metadata rows | {len(report["missing_metadata"])} |
| Duplicate hashes | {len(report["duplicate_hashes"])} |
| Mixed-lesson chunks | {len(report["mixed_lessons"])} |

## Checks

{checks_md}

## Remaining Issues

{json.dumps(report["remaining_issues"], ensure_ascii=False)}
"""
    VALIDATION_MD.write_text(md, encoding="utf-8")


def main() -> None:
    report = validate()
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["validation_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
