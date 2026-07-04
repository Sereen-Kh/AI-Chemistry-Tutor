"""Reviewed curriculum metadata guard for embedding pipelines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_DIR


REVIEWED_METADATA_RELATIVE_PATH = "data/processed/curriculum/reviewed_curriculum_metadata.json"
REPO_ROOT = Path(__file__).resolve().parents[4]
REVIEWED_METADATA_PATH = (
    REPO_ROOT / REVIEWED_METADATA_RELATIVE_PATH
    if (REPO_ROOT / "data/processed").exists()
    else PROJECT_DIR / REVIEWED_METADATA_RELATIVE_PATH
)

MISSING_METADATA_CODE = "REVIEWED_CURRICULUM_METADATA_MISSING"
NOT_READY_CODE = "CURRICULUM_METADATA_NOT_READY_FOR_EMBEDDING"

DEFAULT_REQUIRED_CHUNK_METADATA = [
    "lesson_id",
    "unit_id",
    "source_type",
    "printed_page_start",
    "printed_page_end",
    "quality_status",
    "reviewed_metadata_version",
]


class ReviewedCurriculumMetadataError(RuntimeError):
    """Raised when embedding is attempted without reviewed curriculum metadata."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


def load_reviewed_curriculum_metadata(*, require_ready: bool = False) -> dict[str, Any]:
    """Load reviewed curriculum metadata and optionally require embedding readiness."""

    if not REVIEWED_METADATA_PATH.exists():
        raise ReviewedCurriculumMetadataError(MISSING_METADATA_CODE)
    payload = json.loads(REVIEWED_METADATA_PATH.read_text(encoding="utf-8"))
    if require_ready and payload.get("ready_for_embedding") is not True:
        raise ReviewedCurriculumMetadataError(NOT_READY_CODE)
    return payload


def reviewed_metadata_version(metadata: dict[str, Any] | None = None) -> str:
    payload = metadata or load_reviewed_curriculum_metadata(require_ready=True)
    return str(payload.get("version") or "")


def required_chunk_metadata(metadata: dict[str, Any] | None = None) -> list[str]:
    payload = metadata or load_reviewed_curriculum_metadata(require_ready=True)
    contract = payload.get("embedding_contract") or {}
    return list(contract.get("required_chunk_metadata") or DEFAULT_REQUIRED_CHUNK_METADATA)


def ensure_reviewed_metadata_ready() -> dict[str, Any]:
    """Fail-fast guard for any embedding/re-embedding entry point."""

    return load_reviewed_curriculum_metadata(require_ready=True)


def _metadata_dict(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _chunk_value(chunk: Any, field: str) -> Any:
    if isinstance(chunk, dict):
        metadata = _metadata_dict(chunk.get("metadata") or chunk.get("metadata_json"))
        if field in metadata:
            return metadata[field]
        if field == "printed_page_start":
            return chunk.get("printed_page_start") or chunk.get("page_start") or chunk.get("page_number")
        if field == "printed_page_end":
            return chunk.get("printed_page_end") or chunk.get("page_end") or chunk.get("page_number")
        return chunk.get(field)

    metadata = _metadata_dict(getattr(chunk, "metadata_json", None))
    if field in metadata:
        return metadata[field]
    if field == "source_type":
        return getattr(chunk, "source_type", None)
    if field == "printed_page_start":
        return metadata.get("printed_page_start") or metadata.get("page_start") or getattr(chunk, "page_number", None)
    if field == "printed_page_end":
        return metadata.get("printed_page_end") or metadata.get("page_end") or getattr(chunk, "page_number", None)
    if field == "quality_status":
        return metadata.get("quality_status")
    return metadata.get(field)


def chunk_reviewed_metadata_issues(
    chunk: Any,
    metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Return missing/invalid reviewed metadata fields for a chunk-like object."""

    payload = metadata or load_reviewed_curriculum_metadata(require_ready=True)
    missing: list[str] = []
    contract = payload.get("embedding_contract") or {}
    optional_lesson_scopes = set(contract.get("lesson_id_optional_for_content_scopes") or [])
    for field in required_chunk_metadata(payload):
        value = _chunk_value(chunk, field)
        if (
            field == "lesson_id"
            and _chunk_value(chunk, "content_scope") in optional_lesson_scopes
            and _chunk_value(chunk, "unit_id") not in (None, "", [])
        ):
            continue
        if value in (None, "", []):
            missing.append(field)
    source_type = _chunk_value(chunk, "source_type")
    allowed_source_types = set(contract.get("allowed_source_types") or ["textbook", "solution_book"])
    if source_type and source_type not in allowed_source_types:
        missing.append("source_type_not_allowed")
    return sorted(set(missing))


def chunk_quality_status(chunk: Any) -> str:
    value = _chunk_value(chunk, "quality_status")
    return str(value or "")


def chunk_is_blocked(chunk: Any, metadata: dict[str, Any] | None = None) -> bool:
    payload = metadata or load_reviewed_curriculum_metadata(require_ready=True)
    blocked_statuses = set(
        (payload.get("embedding_contract") or {}).get("blocked_quality_statuses")
        or ["blocked"]
    )
    return chunk_quality_status(chunk) in blocked_statuses


def chunk_is_embedding_ready(
    chunk: Any,
    metadata: dict[str, Any] | None = None,
) -> tuple[bool, str | None, list[str]]:
    """Return readiness, skip reason, and missing fields for one chunk."""

    payload = metadata or load_reviewed_curriculum_metadata(require_ready=True)
    if chunk_is_blocked(chunk, payload):
        return False, "blocked_quality_status", []
    missing = chunk_reviewed_metadata_issues(chunk, payload)
    if missing:
        return False, "missing_reviewed_metadata", missing
    return True, None, []


def metadata_with_reviewed_version(
    raw: dict | list | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = _metadata_dict(raw)
    version = reviewed_metadata_version(metadata)
    return {
        **base,
        "reviewed_metadata_version": version,
        "reviewed_curriculum_metadata_path": REVIEWED_METADATA_RELATIVE_PATH,
    }
