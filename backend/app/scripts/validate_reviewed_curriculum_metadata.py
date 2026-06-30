"""Validate reviewed curriculum metadata bundle.

Run from ``src/backend``:

    python -m app.scripts.validate_reviewed_curriculum_metadata
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.reviewed_curriculum_metadata import (
    DEFAULT_REQUIRED_CHUNK_METADATA,
    REVIEWED_METADATA_PATH,
    REVIEWED_METADATA_RELATIVE_PATH,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parents[1]
REPORT_DIR = REPO_ROOT / "reports/reviewed_curriculum_metadata"
VALIDATION_JSON = REPORT_DIR / "validation_report.json"
VALIDATION_MD = REPORT_DIR / "validation_report.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _repo_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _ready_lesson_issues(lesson_map_path: Path) -> list[dict[str, Any]]:
    if not lesson_map_path.exists():
        return []
    payload = _load_json(lesson_map_path)
    issues: list[dict[str, Any]] = []
    for lesson in payload.get("lessons", []):
        status = lesson.get("quality_status") or lesson.get("quality", {}).get("status")
        if status != "ready":
            continue
        missing = [
            field
            for field in ("lesson_id", "printed_page_start", "printed_page_end")
            if lesson.get(field) in (None, "", [])
        ]
        if missing:
            issues.append({"lesson_id": lesson.get("lesson_id"), "missing": missing})
    return issues


def _solution_chunk_issues(chunks_path: Path) -> dict[str, list[dict[str, Any]]]:
    missing_source_type: list[dict[str, Any]] = []
    missing_quality_status: list[dict[str, Any]] = []
    missing_link: list[dict[str, Any]] = []
    for chunk in _read_jsonl(chunks_path):
        chunk_id = chunk.get("chunk_id")
        if chunk.get("source_type") != "solution_book":
            missing_source_type.append({"chunk_id": chunk_id, "source_type": chunk.get("source_type")})
        if not chunk.get("quality_status"):
            missing_quality_status.append({"chunk_id": chunk_id})
        if not chunk.get("linked_textbook_lesson_id") and not (chunk.get("metadata") or {}).get("needs_manual_review"):
            missing_link.append({"chunk_id": chunk_id})
    return {
        "missing_source_type": missing_source_type,
        "missing_quality_status": missing_quality_status,
        "missing_link": missing_link,
    }


def validate() -> dict[str, Any]:
    blocking_issues: list[str] = []
    warnings: list[str] = []
    missing_paths: list[str] = []

    if not REVIEWED_METADATA_PATH.exists():
        return {
            "validation_status": "failed",
            "metadata_path": REVIEWED_METADATA_RELATIVE_PATH,
            "ready_for_embedding": False,
            "missing_paths": [REVIEWED_METADATA_RELATIVE_PATH],
            "blocking_issues": ["reviewed_curriculum_metadata_missing"],
            "warnings": [],
        }

    metadata = _load_json(REVIEWED_METADATA_PATH)
    paths = metadata.get("paths") or {}
    contract = metadata.get("embedding_contract") or {}
    quality = metadata.get("quality") or {}

    if not metadata.get("version"):
        blocking_issues.append("version_missing")
    if metadata.get("status") not in {"reviewed", "blocked"}:
        blocking_issues.append("status_must_be_reviewed_or_blocked")

    for key, value in paths.items():
        if not value:
            missing_paths.append(key)
            continue
        if not _repo_path(str(value)).exists():
            missing_paths.append(str(value))

    lesson_map_path = _repo_path(str(paths.get("textbook_lesson_map_path", "")))
    solution_chunks_path = _repo_path(str(paths.get("solution_chunks_path", "")))
    ready_lesson_issues = _ready_lesson_issues(lesson_map_path)
    solution_chunk_issues = _solution_chunk_issues(solution_chunks_path)

    if 190 in (quality.get("textbook_needs_ocr_pages") or []):
        blocking_issues.append("page_190_in_needs_ocr_pages")
    if 190 in (quality.get("textbook_needs_vision_pages") or []):
        blocking_issues.append("page_190_in_needs_vision_pages")
    if int(quality.get("solution_chunks_bad_endings") or 0) != 0:
        blocking_issues.append("solution_chunks_bad_endings_not_zero")
    if ready_lesson_issues:
        blocking_issues.append("ready_lessons_missing_required_fields")
    if solution_chunk_issues["missing_source_type"]:
        blocking_issues.append("solution_chunks_missing_source_type")
    if solution_chunk_issues["missing_quality_status"]:
        blocking_issues.append("solution_chunks_missing_quality_status")
    if solution_chunk_issues["missing_link"]:
        warnings.append("solution_chunks_missing_link_without_manual_review")

    declared_fields = set(contract.get("required_chunk_metadata") or [])
    missing_contract_fields = sorted(set(DEFAULT_REQUIRED_CHUNK_METADATA) - declared_fields)
    if missing_contract_fields:
        blocking_issues.append("required_embedding_metadata_fields_not_declared")

    manual_review_required = quality.get("manual_review_required") or []
    ready_for_embedding = metadata.get("ready_for_embedding") is True
    readiness_blockers = [
        issue
        for issue in [
            *blocking_issues,
            *(metadata.get("blocking_issues") or []),
        ]
        if issue
    ]
    if ready_for_embedding and (readiness_blockers or manual_review_required):
        blocking_issues.append("ready_for_embedding_true_with_remaining_blockers")
    if not ready_for_embedding and metadata.get("status") != "blocked":
        blocking_issues.append("not_ready_metadata_must_have_blocked_status")

    report = {
        "validation_status": "passed" if not blocking_issues and not missing_paths else "failed",
        "metadata_path": REVIEWED_METADATA_RELATIVE_PATH,
        "ready_for_embedding": ready_for_embedding,
        "missing_paths": missing_paths,
        "blocking_issues": sorted(set(blocking_issues)),
        "warnings": warnings,
        "ready_lesson_issues": ready_lesson_issues,
        "solution_chunk_issues": solution_chunk_issues,
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md = f"""# Reviewed Curriculum Metadata Validation Report

Validation status: `{report["validation_status"]}`

| Field | Value |
| --- | --- |
| Metadata path | `{report["metadata_path"]}` |
| ready_for_embedding | {report["ready_for_embedding"]} |
| Missing paths | {len(report["missing_paths"])} |
| Blocking issues | {len(report["blocking_issues"])} |
| Warnings | {len(report["warnings"])} |

## Blocking Issues

{json.dumps(report["blocking_issues"], ensure_ascii=False, indent=2)}

## Warnings

{json.dumps(report["warnings"], ensure_ascii=False, indent=2)}
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
