"""Read-only operational summary for the production RAG pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.ingestion import IngestionJob
from app.models.rag_logging import RagQueryLog
from app.services.rag_runtime import (
    active_reviewed_metadata_version,
    load_json_report,
    production_gate_status,
    student_retrieval_is_enabled,
)


def _dict(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _report_summary(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "status": report.get("status") or report.get("result"),
        "reviewed_metadata_version": report.get("reviewed_metadata_version"),
        "embedding_model": report.get("embedding_model"),
        "metrics": report.get("metrics") or report.get("summary") or {},
        "threshold_failures": report.get("threshold_failures") or [],
        "generated_at": report.get("generated_at"),
        "report_json_path": report.get("report_json_path"),
        "report_markdown_path": report.get("report_markdown_path"),
    }


def _job_summary(job: IngestionJob | None) -> dict[str, Any] | None:
    if job is None:
        return None
    result = _dict(job.result_json)
    return {
        "job_id": job.job_uid,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "embedding_model": result.get("embedding_model"),
        "reviewed_metadata_version": result.get("reviewed_metadata_version"),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "errors": job.errors_json,
    }


def _percentile_95(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * 0.95)))
    return float(ordered[index])


def build_rag_operations(db: Session, *, window_hours: int = 24) -> dict[str, Any]:
    """Aggregate existing logs and reports without changing application state."""

    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    logs = list(
        db.scalars(
            select(RagQueryLog)
            .options(selectinload(RagQueryLog.retrieved_chunks))
            .where(RagQueryLog.created_at >= since)
            .order_by(RagQueryLog.created_at.desc())
        ).unique().all()
    )
    query_volume = len(logs)
    no_result_count = sum(log.result_count == 0 for log in logs)
    low_confidence_count = sum(bool(log.low_confidence) for log in logs)
    latencies = [int(log.retrieval_latency_ms) for log in logs if log.retrieval_latency_ms is not None]
    source_distribution: dict[str, int] = {}
    quality_counts = {"ready": 0, "needs_review": 0, "blocked": 0, "unknown": 0}
    missing_citation_metadata_count = 0
    for log in logs:
        metadata = _dict(log.metadata_json)
        for source_type, count in _dict(metadata.get("source_type_counts")).items():
            source_distribution[str(source_type)] = source_distribution.get(str(source_type), 0) + int(count)
        for quality, count in _dict(metadata.get("quality_status_counts")).items():
            key = str(quality) if str(quality) in quality_counts else "unknown"
            quality_counts[key] += int(count)
        missing_citation_metadata_count += int(metadata.get("missing_citation_metadata_count") or 0)

    jobs = list(db.scalars(select(IngestionJob).order_by(IngestionJob.updated_at.desc()).limit(50)).all())
    latest_embedding_job = next(
        (
            job
            for job in jobs
            if "re-embedding" in str(job.message or "").lower()
            or _dict(job.result_json).get("embedding_model")
        ),
        None,
    )
    evaluation = load_json_report(settings.rag_evaluation_report_path)
    qa = load_json_report(settings.rag_qa_report_path)
    gate = production_gate_status()
    degraded: list[str] = list(gate.get("blocking_issues") or [])
    if query_volume and no_result_count / query_volume > 0.10:
        degraded.append("NO_RESULT_RATE_HIGH")
    if query_volume and low_confidence_count / query_volume > 0.25:
        degraded.append("LOW_CONFIDENCE_RATE_HIGH")
    if missing_citation_metadata_count:
        degraded.append("CITATION_METADATA_INCOMPLETE")
    degraded = list(dict.fromkeys(degraded))

    return {
        "status": "healthy" if not degraded else "degraded",
        "window_hours": window_hours,
        "active_reviewed_metadata_version": active_reviewed_metadata_version() or None,
        "embedding_model": settings.gemini_embedding_model,
        "student_retrieval_enabled": student_retrieval_is_enabled(),
        "production_gate_required": bool(settings.rag_require_production_gate),
        "production_gate_status": gate,
        "query_volume": query_volume,
        "no_result_rate": round(no_result_count / query_volume, 4) if query_volume else 0.0,
        "low_confidence_rate": round(low_confidence_count / query_volume, 4) if query_volume else 0.0,
        "average_retrieval_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "p95_retrieval_latency_ms": _percentile_95(latencies),
        "source_type_distribution": source_distribution,
        "quality_status_counts": quality_counts,
        "missing_citation_metadata_count": missing_citation_metadata_count,
        "latest_embedding_job": _job_summary(latest_embedding_job),
        "latest_evaluation": _report_summary(evaluation),
        "latest_student_flow_qa": _report_summary(qa),
        "degraded_reasons": degraded,
    }
