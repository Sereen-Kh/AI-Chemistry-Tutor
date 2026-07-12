"""Production activation, cache namespace, and emergency RAG controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_DIR, settings
from app.services.reviewed_curriculum_metadata import (
    ReviewedCurriculumMetadataError,
    load_reviewed_curriculum_metadata,
)

PRODUCTION_GATE_NOT_READY = "RAG_PRODUCTION_GATE_NOT_READY"
STUDENT_RETRIEVAL_DISABLED = "RAG_STUDENT_RETRIEVAL_DISABLED"


class RagProductionGateError(RuntimeError):
    """Raised when explicitly enabled production RAG cannot be activated."""

    def __init__(self, issues: list[str]) -> None:
        self.code = PRODUCTION_GATE_NOT_READY
        self.issues = list(dict.fromkeys(issues))
        super().__init__(f"{self.code}: {', '.join(self.issues)}")


def resolve_runtime_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_DIR / candidate


def load_json_report(path: str | Path) -> dict[str, Any] | None:
    resolved = resolve_runtime_path(path)
    if not resolved.exists():
        return None
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def active_reviewed_metadata_version() -> str:
    """Return the configured production version without consulting a provider."""

    return str(settings.rag_active_reviewed_metadata_version or "").strip()


def rag_cache_namespace() -> str:
    """Version every RAG cache by reviewed metadata and embedding model."""

    raw = f"{active_reviewed_metadata_version()}|{settings.gemini_embedding_model}|{settings.embedding_dimension}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def student_retrieval_is_enabled() -> bool:
    return bool(settings.rag_student_retrieval_enabled)


def production_gate_status() -> dict[str, Any]:
    """Validate report/version activation prerequisites without mutating state."""

    active_version = active_reviewed_metadata_version()
    embedding_model = settings.gemini_embedding_model
    issues: list[str] = []

    try:
        reviewed = load_reviewed_curriculum_metadata(require_ready=True)
    except ReviewedCurriculumMetadataError as exc:
        reviewed = {}
        issues.append(exc.code)

    reviewed_version = str(reviewed.get("version") or "")
    if not active_version:
        issues.append("RAG_ACTIVE_REVIEWED_METADATA_VERSION_MISSING")
    elif reviewed_version and reviewed_version != active_version:
        issues.append("REVIEWED_METADATA_VERSION_MISMATCH")
    if embedding_model != "gemini-embedding-001" or settings.embedding_dimension != 768:
        issues.append("EMBEDDING_MODEL_MISMATCH")
    if settings.embedding_provider not in {"gemini", "auto"} or settings.allow_hash_embeddings or settings.allow_local_embeddings:
        issues.append("UNSAFE_EMBEDDING_FALLBACK_CONFIGURED")

    evaluation = load_json_report(settings.rag_evaluation_report_path)
    qa = load_json_report(settings.rag_qa_report_path)

    def validate_report(report: dict[str, Any] | None, *, missing_code: str, failed_code: str) -> None:
        if report is None:
            issues.append(missing_code)
            return
        report_status = str(report.get("status") or report.get("result") or "")
        report_passed = report.get("passed") is True or report_status == "passed"
        if not report_passed:
            issues.append(failed_code)
        if str(report.get("reviewed_metadata_version") or "") != active_version:
            issues.append("REVIEWED_METADATA_VERSION_MISMATCH")
        if str(report.get("embedding_model") or "") != embedding_model:
            issues.append("EMBEDDING_MODEL_MISMATCH")

    validate_report(
        evaluation,
        missing_code="RAG_EVALUATION_REPORT_MISSING",
        failed_code="RAG_EVALUATION_GATE_NOT_PASSED",
    )
    validate_report(
        qa,
        missing_code="RAG_QA_REPORT_MISSING",
        failed_code="RAG_QA_GATE_NOT_PASSED",
    )
    if qa is not None and qa.get("mode") != "integration":
        issues.append("RAG_QA_LIVE_REPORT_REQUIRED")

    issues = list(dict.fromkeys(issues))
    return {
        "status": "ready" if not issues else "blocked",
        "student_retrieval_enabled": student_retrieval_is_enabled(),
        "production_gate_required": bool(settings.rag_require_production_gate),
        "active_reviewed_metadata_version": active_version,
        "reviewed_metadata_version": reviewed_version or None,
        "embedding_model": embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "evaluation_status": (evaluation or {}).get("status") or (evaluation or {}).get("result") or "missing",
        "qa_status": (qa or {}).get("status") or (qa or {}).get("result") or "missing",
        "blocking_issues": issues,
    }


def assert_production_activation_ready() -> dict[str, Any]:
    """Fail startup only when the operator explicitly requires the gate."""

    status = production_gate_status()
    if settings.rag_require_production_gate and student_retrieval_is_enabled() and status["blocking_issues"]:
        raise RagProductionGateError(status["blocking_issues"])
    return status


def assert_database_activation_ready(db) -> dict[str, Any]:
    """Require a complete eligible index when production gating is active."""

    if not (settings.rag_require_production_gate and student_retrieval_is_enabled()):
        return {"status": "not_required", "can_evaluate": False, "blocking_issues": []}
    from app.services.rag_preflight import build_rag_preflight

    preflight = build_rag_preflight(db)
    if not preflight.get("can_evaluate"):
        issues = [
            *(preflight.get("blocking_issues") or []),
            *(preflight.get("warnings") or []),
        ]
        raise RagProductionGateError(issues or ["EMBEDDING_INDEX_INCOMPLETE"])
    return preflight
