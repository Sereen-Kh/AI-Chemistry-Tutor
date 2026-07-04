"""Admin APIs for RAG maintenance, evaluation, and observability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import PROJECT_DIR
from app.core.dependencies import require_admin
from app.database import get_async_db
from app.models.rag_logging import RagQueryLog
from app.schemas.rag import (
    RagEvaluationRequest,
    RagEvaluationResponse,
    RagQueryLogResponse,
    RagReembedRequest,
    RagReembedResponse,
    RagReembedStatusResponse,
)
from app.services.rag_evaluation import evaluate_rag_dataset
from app.services.reviewed_curriculum_metadata import (
    NOT_READY_CODE,
    ReviewedCurriculumMetadataError,
    ensure_reviewed_metadata_ready,
)
from app.workers.celery_app import celery_app
from app.workers.rag_tasks import reembed_rag_chunks_task

router = APIRouter(prefix="/admin/rag", tags=["admin-rag"])


def _project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_DIR / candidate


def _async_result_payload(result: AsyncResult) -> dict[str, Any] | None:
    info = result.info
    return info if isinstance(info, dict) else None


@router.post("/reembed", response_model=RagReembedResponse)
def start_rag_reembed(
    request: RagReembedRequest,
    _admin=Depends(require_admin),
):
    try:
        ensure_reviewed_metadata_ready()
    except ReviewedCurriculumMetadataError as exc:
        status_code = 409 if exc.code == NOT_READY_CODE else 404
        raise HTTPException(status_code=status_code, detail=exc.code) from exc
    try:
        task = reembed_rag_chunks_task.delay(
            source_id=request.source_id,
            source_type=request.source_type,
            batch_size=request.batch_size,
            dry_run=request.dry_run,
            force=request.force,
            resume_failed=request.resume_failed,
        )
    except Exception as exc:  # pragma: no cover - broker availability
        raise HTTPException(status_code=503, detail=f"Could not queue RAG re-embedding job: {exc}") from exc
    return RagReembedResponse(
        job_id=task.id,
        status="queued",
        message="RAG re-embedding job queued.",
    )


@router.get("/reembed/status/{job_id}", response_model=RagReembedStatusResponse)
def get_rag_reembed_status(
    job_id: str,
    _admin=Depends(require_admin),
):
    result = AsyncResult(job_id, app=celery_app)
    error = None
    payload = _async_result_payload(result) or {}
    if result.failed():
        error = str(result.info)
    return RagReembedStatusResponse(
        job_id=job_id,
        status=result.status.lower(),
        progress=int(payload.get("progress") or 0),
        total_chunks=int(payload.get("total_chunks") or 0),
        total_candidates=int(payload.get("total_candidates") or 0),
        processed=int(payload.get("processed") or 0),
        updated=int(payload.get("updated") or 0),
        skipped=int(payload.get("skipped") or 0),
        failed=int(payload.get("failed") or 0),
        embedding_model=payload.get("embedding_model"),
        reviewed_metadata_version=payload.get("reviewed_metadata_version"),
        metadata_ready=bool(payload.get("metadata_ready") or False),
        skipped_missing_metadata_count=int(payload.get("skipped_missing_metadata_count") or 0),
        skipped_blocked_count=int(payload.get("skipped_blocked_count") or 0),
        dry_run=bool(payload.get("dry_run") or False),
        source_id=payload.get("source_id"),
        source_type=payload.get("source_type"),
        result=payload,
        error=error,
    )


@router.post("/evaluate", response_model=RagEvaluationResponse)
async def run_rag_evaluation(
    request: RagEvaluationRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await evaluate_rag_dataset(
        db,
        dataset_path=request.dataset_path,
        report_dir=request.report_dir,
        top_k=request.top_k,
    )
    return RagEvaluationResponse(
        status="passed" if result.passed else "failed_thresholds",
        passed=result.passed,
        report_json_path=result.report_json_path,
        report_markdown_path=result.report_markdown_path,
        metrics=result.metrics,
        threshold_failures=result.threshold_failures,
    )


@router.get("/evaluation/latest", response_model=RagEvaluationResponse)
def get_latest_rag_evaluation(
    report_path: str = "data/eval/reports/rag_eval_latest.json",
    _admin=Depends(require_admin),
):
    resolved = _project_path(report_path)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="No RAG evaluation report found.")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return RagEvaluationResponse(
        status="passed" if payload.get("passed") else "failed_thresholds",
        passed=bool(payload.get("passed")),
        report_json_path=str(payload.get("report_json_path") or resolved),
        report_markdown_path=str(payload.get("report_markdown_path") or resolved.with_suffix(".md")),
        metrics=payload.get("metrics") or {},
        threshold_failures=payload.get("threshold_failures") or [],
    )


@router.get("/query-logs", response_model=list[RagQueryLogResponse])
async def list_rag_query_logs(
    user_id: int | None = None,
    route: str | None = None,
    low_confidence: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = select(RagQueryLog).options(selectinload(RagQueryLog.retrieved_chunks))
    if user_id is not None:
        stmt = stmt.where(RagQueryLog.user_id == user_id)
    if route:
        stmt = stmt.where(RagQueryLog.route == route)
    if low_confidence is not None:
        stmt = stmt.where(RagQueryLog.low_confidence.is_(low_confidence))
    stmt = stmt.order_by(RagQueryLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


@router.get("/query-logs/{log_id}", response_model=RagQueryLogResponse)
async def get_rag_query_log(
    log_id: int,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(RagQueryLog)
        .options(selectinload(RagQueryLog.retrieved_chunks))
        .where(RagQueryLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="RAG query log not found.")
    return log
