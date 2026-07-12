"""Admin APIs for RAG maintenance, evaluation, and observability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.core.config import PROJECT_DIR
from app.core.dependencies import require_admin
from app.database import get_async_db, get_db
from app.models.ingestion import IngestionJob
from app.models.textbook import RagChunk
from app.models.rag_logging import RagQueryLog
from app.schemas.rag import (
    RagChunkExplorerItemResponse,
    RagChunkExplorerResponse,
    RagEvaluationRequest,
    RagEvaluationResponse,
    RagPreflightResponse,
    RagQaResponse,
    RagOperationsResponse,
    RagQueryLogResponse,
    RagReembedRequest,
    RagReembedResponse,
    RagReembedStatusResponse,
    RagSourceStatusResponse,
)
from app.services.rag_evaluation import evaluate_rag_dataset
from app.services.rag_preflight import build_rag_preflight
from app.services.rag_operations import build_rag_operations
from app.services.rag_runtime import load_json_report
from app.services.reviewed_curriculum_metadata import (
    NOT_READY_CODE,
    ReviewedCurriculumMetadataError,
    chunk_reviewed_metadata_issues,
    ensure_reviewed_metadata_ready,
    evaluate_chunk_eligibility,
    load_reviewed_curriculum_metadata,
)
from app.services.reviewed_ingestion_assets import rag_source_status, rag_source_statuses, scan_rag_source
from app.workers.celery_app import celery_app
from app.workers.rag_tasks import reembed_rag_chunks_task

router = APIRouter(prefix="/admin/rag", tags=["admin-rag"])


def _project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_DIR / candidate


def _async_result_payload(result: AsyncResult) -> dict[str, Any] | None:
    info = result.info
    return info if isinstance(info, dict) else None


def _metadata_dict(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _metadata_value(chunk: RagChunk, metadata: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, "", []):
            return value
    for key in keys:
        value = getattr(chunk, key, None)
        if value not in (None, "", []):
            return value
    return None


def _reviewed_metadata_for_explorer() -> dict[str, Any] | None:
    try:
        return load_reviewed_curriculum_metadata(require_ready=False)
    except ReviewedCurriculumMetadataError:
        return None


def _chunk_explorer_item(
    chunk: RagChunk,
    reviewed_metadata: dict[str, Any] | None,
) -> RagChunkExplorerItemResponse:
    metadata = _metadata_dict(chunk.metadata_json)
    decision = None
    if reviewed_metadata:
        decision = evaluate_chunk_eligibility(
            chunk,
            reviewed_metadata,
            legacy=chunk.extraction_method != "reviewed_jsonl",
        )
    missing = decision.missing_fields if decision else chunk_reviewed_metadata_issues(chunk, reviewed_metadata) if reviewed_metadata else []
    quality_status = decision.normalized_quality_status if decision else "needs_review"
    stale = bool(metadata.get("stale") is True)
    visible_embedding_status = "stale" if stale else chunk.embedding_status
    reason_codes = list(decision.reason_codes if decision else ["reviewed_metadata_unavailable"])
    if stale and "stale_reviewed_chunk" not in reason_codes:
        reason_codes.append("stale_reviewed_chunk")
    source_file = chunk.source.file_path if chunk.source is not None else None
    content = chunk.content or ""
    preview = content[:360] + ("…" if len(content) > 360 else "")
    return RagChunkExplorerItemResponse(
        id=chunk.id,
        source_id=chunk.source_id,
        source_type=chunk.source_type,
        source_file=source_file,
        reviewed_chunk_id=metadata.get("reviewed_chunk_id") or metadata.get("chunk_id"),
        content_type=chunk.content_type,
        page_number=chunk.page_number,
        unit_id=_metadata_value(chunk, metadata, "unit_id"),
        lesson_id=_metadata_value(chunk, metadata, "lesson_id"),
        topic_id=chunk.topic_id,
        printed_page_start=_metadata_value(chunk, metadata, "printed_page_start", "page_start", "page_number"),
        printed_page_end=_metadata_value(chunk, metadata, "printed_page_end", "page_end", "page_number"),
        quality_status=quality_status,
        reviewed_metadata_version=metadata.get("reviewed_metadata_version"),
        embedding_status=visible_embedding_status,
        embedding_model=chunk.embedding_model,
        embedding_error=chunk.embedding_error,
        content_hash=metadata.get("content_hash"),
        missing_metadata=missing,
        embedding_allowed=(decision.embedding_allowed and not stale) if decision else False,
        rag_search_allowed=(decision.rag_search_allowed and not stale) if decision else False,
        student_generation_allowed=(decision.student_generation_allowed and not stale) if decision else False,
        warning_required=True if stale else (decision.warning_required if decision else True),
        reason_codes=reason_codes,
        legacy_unmapped=bool(decision and decision.normalized_metadata.get("legacy_unmapped")),
        stale=stale,
        content_preview=preview,
        metadata_json=chunk.metadata_json,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at,
    )


def _matches_optional_filter(actual: Any, expected: str | None) -> bool:
    return expected is None or str(actual) == expected


@router.get("/preflight", response_model=RagPreflightResponse)
def get_rag_preflight(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return a read-only production baseline for the reviewed RAG pipeline."""

    return build_rag_preflight(db)


@router.get("/sources", response_model=list[RagSourceStatusResponse])
def list_rag_sources(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return rag_source_statuses(db)


@router.get("/sources/{source_id}", response_model=RagSourceStatusResponse)
def get_rag_source(
    source_id: str,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    status = rag_source_status(source_id, db=db)
    if status is None:
        raise HTTPException(status_code=404, detail="RAG source not found")
    return status


@router.post("/sources/{source_id}/scan", response_model=RagSourceStatusResponse)
def scan_rag_source_endpoint(
    source_id: str,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    status = scan_rag_source(source_id, db=db)
    if status is None:
        raise HTTPException(status_code=404, detail="RAG source not found")
    return status


@router.get("/chunks", response_model=RagChunkExplorerResponse)
def list_rag_chunks(
    source_type: str | None = None,
    quality_status: str | None = None,
    embedding_status: str | None = None,
    unit_id: str | None = None,
    lesson_id: str | None = None,
    page_start: int | None = Query(default=None, ge=0),
    page_end: int | None = Query(default=None, ge=0),
    reviewed_metadata_version: str | None = None,
    missing_metadata_field: str | None = None,
    legacy_unmapped: bool | None = None,
    embedding_error: str | None = None,
    content_type: str | None = None,
    search: str | None = None,
    missing_metadata: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    reviewed_metadata = _reviewed_metadata_for_explorer()
    stmt = select(RagChunk).order_by(RagChunk.id.asc())
    if source_type:
        stmt = stmt.where(RagChunk.source_type == source_type)
    rows = list(db.scalars(stmt).all())
    global_rows = list(db.scalars(select(RagChunk).order_by(RagChunk.id.asc())).all())

    filtered_items: list[RagChunkExplorerItemResponse] = []
    counts = {
        "total_chunks": 0,
        "ready_chunks": 0,
        "needs_review_chunks": 0,
        "blocked_chunks": 0,
        "missing_metadata_chunks": 0,
        "embedded_chunks": 0,
        "pending_chunks": 0,
        "failed_embedding_chunks": 0,
    }
    def build_counts(items: list[RagChunk]) -> dict[str, int]:
        result = {
            "total_chunks": 0,
            "ready_chunks": 0,
            "needs_review_chunks": 0,
            "blocked_chunks": 0,
            "missing_metadata_chunks": 0,
            "embedded_chunks": 0,
            "pending_chunks": 0,
            "failed_embedding_chunks": 0,
            "stale_chunks": 0,
        }
        for row in items:
            item = _chunk_explorer_item(row, reviewed_metadata)
            result["total_chunks"] += 1
            if item.quality_status == "ready":
                result["ready_chunks"] += 1
            elif item.quality_status == "blocked":
                result["blocked_chunks"] += 1
            else:
                result["needs_review_chunks"] += 1
            if item.missing_metadata:
                result["missing_metadata_chunks"] += 1
            if item.stale:
                result["stale_chunks"] += 1
            elif item.embedding_status == "completed" and row.embedding is not None:
                result["embedded_chunks"] += 1
            elif item.embedding_status == "failed":
                result["failed_embedding_chunks"] += 1
            else:
                result["pending_chunks"] += 1
        return result

    counts = build_counts(global_rows)
    filtered_items: list[RagChunkExplorerItemResponse] = []
    for chunk in rows:
        item = _chunk_explorer_item(chunk, reviewed_metadata)
        has_missing = bool(item.missing_metadata)
        if missing_metadata is not None and has_missing is not missing_metadata:
            continue
        if quality_status and item.quality_status != quality_status:
            continue
        if not _matches_optional_filter(item.unit_id, unit_id):
            continue
        if not _matches_optional_filter(item.lesson_id, lesson_id):
            continue
        if embedding_status and item.embedding_status != embedding_status:
            continue
        if reviewed_metadata_version and item.reviewed_metadata_version != reviewed_metadata_version:
            continue
        if missing_metadata_field and missing_metadata_field not in item.missing_metadata:
            continue
        if legacy_unmapped is not None and item.legacy_unmapped is not legacy_unmapped:
            continue
        if content_type and item.content_type != content_type:
            continue
        if embedding_error and embedding_error.lower() not in (item.embedding_error or "").lower():
            continue
        if page_start is not None and (item.printed_page_end is None or item.printed_page_end < page_start):
            continue
        if page_end is not None and (item.printed_page_start is None or item.printed_page_start > page_end):
            continue
        if search and search.lower() not in (
            f"{item.id} {item.content_preview} {item.unit_id or ''} {item.lesson_id or ''} {item.source_file or ''}"
        ).lower():
            continue
        filtered_items.append(item)

    return RagChunkExplorerResponse(
        total=len(filtered_items),
        filtered_total=len(filtered_items),
        limit=limit,
        offset=offset,
        items=filtered_items[offset : offset + limit],
        counts=counts,
        global_counts=counts,
    )


@router.get("/chunks/{chunk_id}", response_model=RagChunkExplorerItemResponse)
def get_rag_chunk(
    chunk_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    chunk = db.get(RagChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="RAG chunk not found")
    return _chunk_explorer_item(chunk, _reviewed_metadata_for_explorer())


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
    db: Session = Depends(get_db),
):
    result = AsyncResult(job_id, app=celery_app)
    error = None
    payload = _async_result_payload(result) or {}
    stored_job = db.query(IngestionJob).filter(IngestionJob.job_uid == job_id).first()
    if stored_job is not None:
        # The DB record is the durable source for status once Celery result
        # retention expires or the worker restarts.
        payload = {**(stored_job.result_json if isinstance(stored_job.result_json, dict) else {}), **payload}
        if not payload.get("progress"):
            payload["progress"] = stored_job.progress
        if not payload.get("status"):
            payload["status"] = stored_job.status
        if result.status in {"PENDING", "FAILURE"}:
            payload["error"] = stored_job.errors_json
    if result.failed():
        error = str(result.info)
    elif stored_job is not None and stored_job.status == "failed":
        error = str(stored_job.errors_json or stored_job.message)
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
        skipped_stale_count=int(payload.get("skipped_stale_count") or 0),
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
        status=result.status,
        passed=result.passed,
        reviewed_metadata_version=result.reviewed_metadata_version,
        embedding_model=result.embedding_model,
        preconditions=result.preconditions,
        report_json_path=result.report_json_path,
        report_markdown_path=result.report_markdown_path,
        metrics=result.metrics,
        threshold_failures=result.threshold_failures,
        failed_cases=result.failed_cases,
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
        status=str(payload.get("status") or ("passed" if payload.get("passed") else "failed")),
        passed=bool(payload.get("passed")),
        reviewed_metadata_version=payload.get("reviewed_metadata_version"),
        embedding_model=payload.get("embedding_model"),
        preconditions=payload.get("preconditions") or {},
        report_json_path=str(payload.get("report_json_path") or resolved),
        report_markdown_path=str(payload.get("report_markdown_path") or resolved.with_suffix(".md")),
        metrics=payload.get("metrics") or {},
        threshold_failures=payload.get("threshold_failures") or [],
        failed_cases=payload.get("failed_cases") or [],
    )


@router.get("/qa/latest", response_model=RagQaResponse)
def get_latest_rag_qa(
    report_path: str = "backend/reports/rag_qa_report.json",
    _admin=Depends(require_admin),
):
    resolved = _project_path(report_path)
    payload = load_json_report(resolved)
    if payload is None:
        raise HTTPException(status_code=404, detail="No student-flow RAG QA report found.")
    return RagQaResponse(
        status=str(payload.get("status") or "failed"),
        reviewed_metadata_version=payload.get("reviewed_metadata_version"),
        embedding_model=payload.get("embedding_model"),
        preconditions=payload.get("preconditions") or {},
        metrics=payload.get("metrics") or payload.get("summary") or {},
        threshold_failures=payload.get("threshold_failures") or [],
        failed_cases=payload.get("failed_cases") or [],
        report_json_path=str(resolved),
        report_markdown_path=str(resolved.with_suffix(".md")) if resolved.with_suffix(".md").exists() else None,
    )


@router.get("/operations", response_model=RagOperationsResponse)
def get_rag_operations(
    window_hours: int = Query(default=24, ge=1, le=24 * 30),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return build_rag_operations(db, window_hours=window_hours)


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
