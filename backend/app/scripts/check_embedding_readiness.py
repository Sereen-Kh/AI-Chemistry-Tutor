"""Dry-run embedding readiness check for reviewed curriculum metadata.

Run from ``src/backend``:

    python -m app.scripts.check_embedding_readiness
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
READINESS_JSON = REPORT_DIR / "embedding_readiness_report.json"
READINESS_MD = REPORT_DIR / "embedding_readiness_report.md"
TEXTBOOK_PREVIEW = REPO_ROOT / "data/processed/chunk_preview/textbook_chunks_preview.jsonl"


def _read_json(path: Path) -> dict[str, Any]:
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


def _value(chunk: dict[str, Any], field: str) -> Any:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    aliases = {
        "printed_page_start": ["printed_page_start", "page_start"],
        "printed_page_end": ["printed_page_end", "page_end"],
    }
    for key in [field, *aliases.get(field, [])]:
        if chunk.get(key) not in (None, "", []):
            return chunk.get(key)
        if metadata.get(key) not in (None, "", []):
            return metadata.get(key)
    return None


def _chunk_missing_fields(chunk: dict[str, Any], required_fields: list[str]) -> list[str]:
    return [
        field
        for field in required_fields
        if _value(chunk, field) in (None, "", [])
    ]


def _scan_chunks(
    path: Path,
    *,
    source_type: str,
    required_fields: list[str],
    blocked_statuses: set[str],
) -> dict[str, Any]:
    rows = _read_jsonl(path)
    ready = 0
    skipped_missing_metadata = 0
    skipped_blocked = 0
    skipped_needs_review = 0
    examples: list[dict[str, Any]] = []
    for chunk in rows:
        chunk_source_type = _value(chunk, "source_type")
        missing = _chunk_missing_fields(chunk, required_fields)
        if chunk_source_type != source_type and "source_type" not in missing:
            missing.append("source_type")
        quality_status = _value(chunk, "quality_status")
        if quality_status in blocked_statuses:
            skipped_blocked += 1
            continue
        if missing:
            skipped_missing_metadata += 1
            if len(examples) < 10:
                examples.append(
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "source_type": chunk_source_type,
                        "missing_metadata": sorted(set(missing)),
                    }
                )
            continue
        if quality_status != "ready":
            skipped_needs_review += 1
            continue
        ready += 1
    return {
        "path": str(path.relative_to(REPO_ROOT)) if path.exists() else str(path),
        "exists": path.exists(),
        "total": len(rows),
        "ready": ready,
        "skipped_missing_metadata": skipped_missing_metadata,
        "skipped_blocked": skipped_blocked,
        "skipped_needs_review": skipped_needs_review,
        "missing_metadata_examples": examples,
    }


def check() -> dict[str, Any]:
    if not REVIEWED_METADATA_PATH.exists():
        report = {
            "ready_for_embedding": False,
            "reviewed_metadata_version": None,
            "textbook_chunks_ready": 0,
            "solution_chunks_ready": 0,
            "chunks_skipped_missing_metadata": 0,
            "chunks_skipped_blocked": 0,
            "chunks_skipped_needs_review": 0,
            "can_run_embedding": False,
            "blocking_issues": ["REVIEWED_CURRICULUM_METADATA_MISSING"],
        }
        return report

    metadata = _read_json(REVIEWED_METADATA_PATH)
    contract = metadata.get("embedding_contract") or {}
    required_fields = list(contract.get("required_chunk_metadata") or DEFAULT_REQUIRED_CHUNK_METADATA)
    blocked_statuses = set(contract.get("blocked_quality_statuses") or ["blocked"])
    paths = metadata.get("paths") or {}
    solution_chunks_path = _repo_path(str(paths.get("solution_chunks_path") or ""))

    textbook = _scan_chunks(
        TEXTBOOK_PREVIEW,
        source_type="textbook",
        required_fields=required_fields,
        blocked_statuses=blocked_statuses,
    )
    solution = _scan_chunks(
        solution_chunks_path,
        source_type="solution_book",
        required_fields=required_fields,
        blocked_statuses=blocked_statuses,
    )

    chunks_skipped_missing_metadata = (
        textbook["skipped_missing_metadata"] + solution["skipped_missing_metadata"]
    )
    chunks_skipped_blocked = textbook["skipped_blocked"] + solution["skipped_blocked"]
    chunks_skipped_needs_review = (
        textbook["skipped_needs_review"] + solution["skipped_needs_review"]
    )
    blocking_issues = list(metadata.get("blocking_issues") or [])
    if metadata.get("ready_for_embedding") is not True:
        blocking_issues.append("CURRICULUM_METADATA_NOT_READY_FOR_EMBEDDING")
    if chunks_skipped_missing_metadata:
        blocking_issues.append("chunks_missing_required_reviewed_metadata")

    can_run_embedding = (
        metadata.get("ready_for_embedding") is True
        and chunks_skipped_missing_metadata == 0
        and chunks_skipped_blocked == 0
        and textbook["ready"] + solution["ready"] > 0
    )

    report = {
        "ready_for_embedding": metadata.get("ready_for_embedding") is True,
        "reviewed_metadata_version": metadata.get("version"),
        "textbook_chunks_ready": textbook["ready"],
        "solution_chunks_ready": solution["ready"],
        "chunks_skipped_missing_metadata": chunks_skipped_missing_metadata,
        "chunks_skipped_blocked": chunks_skipped_blocked,
        "chunks_skipped_needs_review": chunks_skipped_needs_review,
        "can_run_embedding": can_run_embedding,
        "textbook": textbook,
        "solution_book": solution,
        "blocking_issues": sorted(set(blocking_issues)),
        "metadata_path": REVIEWED_METADATA_RELATIVE_PATH,
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    READINESS_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md = f"""# Embedding Readiness Report

This is a dry-run metadata check only. It does not call an embedding API and does not write to the database.

| Field | Value |
| --- | --- |
| ready_for_embedding | {report["ready_for_embedding"]} |
| reviewed_metadata_version | {report.get("reviewed_metadata_version")} |
| textbook_chunks_ready | {report["textbook_chunks_ready"]} |
| solution_chunks_ready | {report["solution_chunks_ready"]} |
| chunks_skipped_missing_metadata | {report["chunks_skipped_missing_metadata"]} |
| chunks_skipped_blocked | {report["chunks_skipped_blocked"]} |
| chunks_skipped_needs_review | {report["chunks_skipped_needs_review"]} |
| can_run_embedding | {report["can_run_embedding"]} |

## Blocking Issues

{json.dumps(report["blocking_issues"], ensure_ascii=False, indent=2)}
"""
    READINESS_MD.write_text(md, encoding="utf-8")


def main() -> None:
    report = check()
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
