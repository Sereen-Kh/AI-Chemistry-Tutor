"""Reviewed curriculum metadata guard for embedding pipelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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


QualityStatus = Literal["ready", "needs_review", "blocked"]


@dataclass(frozen=True)
class ChunkEligibilityDecision:
    """One shared policy decision for embedding, retrieval, and generation."""

    normalized_quality_status: QualityStatus
    embedding_allowed: bool
    rag_search_allowed: bool
    student_generation_allowed: bool
    warning_required: bool
    missing_fields: list[str]
    reason_codes: list[str]
    normalized_metadata: dict[str, Any]


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
    if field == "printed_page_start":
        return metadata.get("printed_page_start") or metadata.get("page_start") or getattr(chunk, "page_number", None)
    if field == "printed_page_end":
        return metadata.get("printed_page_end") or metadata.get("page_end") or getattr(chunk, "page_number", None)
    return getattr(chunk, field, None)


def _is_real_curriculum_id(value: Any) -> bool:
    return value not in (None, "", []) and not str(value).startswith("unmapped:")


def _chunk_metadata_dict(chunk: Any) -> dict[str, Any]:
    if isinstance(chunk, dict):
        return _metadata_dict(chunk.get("metadata") or chunk.get("metadata_json"))
    return _metadata_dict(getattr(chunk, "metadata_json", None))


def _required_metadata_issues(chunk: Any, payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    contract = payload.get("embedding_contract") or {}
    optional_lesson_scopes = set(contract.get("lesson_id_optional_for_content_scopes") or [])
    content_scope = _chunk_value(chunk, "content_scope")
    for field in required_chunk_metadata(payload):
        value = _chunk_value(chunk, field)
        if field == "lesson_id" and content_scope in optional_lesson_scopes and _is_real_curriculum_id(
            _chunk_value(chunk, "unit_id")
        ):
            continue
        if field in {"unit_id", "lesson_id"}:
            if not _is_real_curriculum_id(value):
                missing.append(field)
        elif value in (None, "", []):
            missing.append(field)
    return sorted(set(missing))


def chunk_reviewed_metadata_issues(
    chunk: Any,
    metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Return missing/invalid reviewed metadata fields for a chunk-like object."""

    payload = metadata or load_reviewed_curriculum_metadata(require_ready=True)
    missing = _required_metadata_issues(chunk, payload)
    contract = payload.get("embedding_contract") or {}
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


def evaluate_chunk_eligibility(
    chunk: Any,
    metadata: dict[str, Any] | None = None,
    *,
    legacy: bool = False,
) -> ChunkEligibilityDecision:
    """Evaluate one chunk against the reviewed curriculum contract.

    ``legacy=True`` is reserved for existing database rows. It permits missing
    curriculum links only after an explicit downgrade to ``needs_review``.
    Fresh reviewed JSONL rows must satisfy the complete metadata contract.
    """

    payload = metadata or load_reviewed_curriculum_metadata(require_ready=True)
    contract = payload.get("embedding_contract") or {}
    allowed_source_types = set(contract.get("allowed_source_types") or ["textbook", "solution_book"])
    blocked_statuses = set(contract.get("blocked_quality_statuses") or ["blocked"])
    normalized = _chunk_metadata_dict(chunk)
    declared_rag_search_allowed = normalized.get("rag_search_allowed")

    for field in (
        "source_type",
        "unit_id",
        "lesson_id",
        "content_scope",
        "printed_page_start",
        "printed_page_end",
        "quality_status",
        "reviewed_metadata_version",
    ):
        value = _chunk_value(chunk, field)
        if value not in (None, "", []):
            normalized.setdefault(field, value)

    content = _chunk_value(chunk, "content") or _chunk_value(chunk, "content_ar")
    source_type = normalized.get("source_type") or _chunk_value(chunk, "source_type")
    raw_quality = str(normalized.get("quality_status") or "").strip().lower()
    normalized_quality: QualityStatus
    reason_codes: list[str] = []
    if raw_quality in blocked_statuses:
        normalized_quality = "blocked"
    elif raw_quality == "ready":
        normalized_quality = "ready"
    elif raw_quality == "needs_review":
        normalized_quality = "needs_review"
    else:
        normalized_quality = "needs_review"
        reason_codes.append("quality_status_normalized")

    unit_id = normalized.get("unit_id") or _chunk_value(chunk, "unit_id")
    lesson_id = normalized.get("lesson_id") or _chunk_value(chunk, "lesson_id")
    missing_curriculum_link = not (_is_real_curriculum_id(unit_id) and _is_real_curriculum_id(lesson_id))
    existing_legacy_flag = bool(
        normalized.get("legacy_unmapped")
        or normalized.get("review_status") == "legacy_unmapped"
        or str(unit_id or "").startswith("unmapped:")
        or str(lesson_id or "").startswith("unmapped:")
    )
    legacy_unmapped = bool((legacy and missing_curriculum_link) or existing_legacy_flag)
    if legacy_unmapped and normalized_quality != "blocked":
        normalized_quality = "needs_review"
        normalized["legacy_unmapped"] = True
        normalized["review_status"] = "legacy_unmapped"
        reason_codes.append("legacy_missing_curriculum_metadata")

    if legacy and normalized.get("reviewed_metadata_version") in (None, "", []):
        normalized["reviewed_metadata_version"] = str(payload.get("version") or "")
    if legacy and normalized.get("quality_status") in (None, "", []):
        normalized["quality_status"] = normalized_quality
    normalized["quality_status"] = normalized_quality

    candidate = {
        "content": content,
        "source_type": source_type,
        "metadata_json": normalized,
    }
    missing = _required_metadata_issues(candidate, payload)
    blocking_missing = list(missing)
    if legacy_unmapped:
        blocking_missing = [field for field in blocking_missing if field not in {"unit_id", "lesson_id"}]

    invalid_source = source_type not in allowed_source_types
    empty_content = not str(content or "").strip()
    if normalized_quality == "blocked":
        reason_codes.append("blocked_quality_status")
    if invalid_source:
        reason_codes.append("invalid_source_type")
    if empty_content:
        reason_codes.append("empty_content")
    if blocking_missing:
        reason_codes.append("missing_required_metadata")

    embedding_allowed = not (
        normalized_quality == "blocked" or invalid_source or empty_content or bool(blocking_missing)
    )
    rag_search_allowed = (
        embedding_allowed
        and normalized_quality in {"ready", "needs_review"}
        and declared_rag_search_allowed is not False
    )
    if declared_rag_search_allowed is False:
        reason_codes.append("rag_search_disabled")
    student_generation_allowed = embedding_allowed and normalized_quality == "ready" and not legacy_unmapped
    warning_required = rag_search_allowed and normalized_quality == "needs_review"
    if embedding_allowed:
        reason_codes.append("eligible_ready" if normalized_quality == "ready" else "eligible_needs_review")

    reason_codes = list(dict.fromkeys(reason_codes))
    normalized["eligibility_reason_codes"] = reason_codes
    normalized["embedding_allowed"] = embedding_allowed
    normalized["rag_search_allowed"] = rag_search_allowed
    normalized["student_generation_allowed"] = student_generation_allowed
    normalized["warning_required"] = warning_required
    return ChunkEligibilityDecision(
        normalized_quality_status=normalized_quality,
        embedding_allowed=embedding_allowed,
        rag_search_allowed=rag_search_allowed,
        student_generation_allowed=student_generation_allowed,
        warning_required=warning_required,
        missing_fields=missing,
        reason_codes=reason_codes,
        normalized_metadata=normalized,
    )


def chunk_is_embedding_ready(
    chunk: Any,
    metadata: dict[str, Any] | None = None,
) -> tuple[bool, str | None, list[str]]:
    """Return readiness, skip reason, and missing fields for one chunk."""

    decision = evaluate_chunk_eligibility(chunk, metadata, legacy=False)
    if decision.embedding_allowed:
        return True, None, decision.missing_fields
    if "blocked_quality_status" in decision.reason_codes:
        return False, "blocked_quality_status", decision.missing_fields
    if "invalid_source_type" in decision.reason_codes:
        return False, "invalid_source_type", decision.missing_fields
    if "empty_content" in decision.reason_codes:
        return False, "empty_content", decision.missing_fields
    return False, "missing_reviewed_metadata", decision.missing_fields


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
