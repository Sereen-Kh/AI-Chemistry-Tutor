"""Celery tasks for RAG maintenance jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.database import AsyncSessionLocal, SessionLocal
from app.models.ingestion import IngestionJob
from app.services.rag_cache import invalidate_rag_caches
from app.services.rag_reembed import redact_embedding_error, reembed_rag_chunks
from app.workers.celery_app import celery_app


def _persist_job(
    job_uid: str,
    *,
    status: str,
    progress: int,
    message: str,
    source_id: int | None = None,
    result: dict[str, Any] | None = None,
    errors: Any = None,
) -> None:
    """Persist worker progress so admin status survives Celery result expiry."""
    with SessionLocal() as db:
        job = db.query(IngestionJob).filter(IngestionJob.job_uid == job_uid).first()
        if job is None:
            job = IngestionJob(job_uid=job_uid, source_id=source_id, status=status, progress=progress, message=message)
            db.add(job)
        else:
            if source_id is not None:
                job.source_id = source_id
            job.status = status
            job.progress = progress
            job.message = message
        if result is not None:
            job.result_json = result
        if errors is not None:
            job.errors_json = errors
        if status in {"completed", "completed_with_errors", "failed", "paused_quota"}:
            job.updated_at = datetime.now(timezone.utc)
        db.commit()


@celery_app.task(bind=True, name="reembed_rag_chunks")
def reembed_rag_chunks_task(
    self,
    source_id: int | None = None,
    source_type: str | None = None,
    batch_size: int = 50,
    dry_run: bool = False,
    force: bool = False,
    resume_failed: bool = False,
    resume_after_chunk_id: int | None = None,
    batch_delay_seconds: float = 0.0,
):
    """Re-embed RAG chunks with the configured production embedding model."""

    async def _run() -> dict:
        job_uid = str(self.request.id)
        _persist_job(
            job_uid,
            status="processing",
            progress=0,
            message="re-embedding started",
            source_id=source_id,
            result={"source_id": source_id, "source_type": source_type},
        )
        self.update_state(state="PROCESSING", meta={"progress": 0, "message": "re-embedding started"})

        def update_progress(payload: dict) -> None:
            self.update_state(state="PROCESSING", meta=payload)
            _persist_job(
                job_uid,
                status="processing",
                progress=int(payload.get("progress") or 0),
                message="re-embedding in progress",
                source_id=source_id,
                result={"source_id": source_id, "source_type": source_type, **payload},
                errors=payload.get("errors"),
            )

        async with AsyncSessionLocal() as db:
            result = await reembed_rag_chunks(
                db,
                source_id=source_id,
                source_type=source_type,
                batch_size=batch_size,
                dry_run=dry_run,
                force=force,
                resume_failed=resume_failed,
                resume_after_chunk_id=resume_after_chunk_id,
                batch_delay_seconds=batch_delay_seconds,
                progress_callback=update_progress,
            )
            payload = result.to_dict()
            payload["cache_invalidation"] = await invalidate_rag_caches()
            _persist_job(
                job_uid,
                status=str(result.status),
                progress=int(result.progress),
                message="re-embedding completed",
                source_id=source_id,
                result={"source_id": source_id, "source_type": source_type, **payload},
                errors=result.errors,
            )
            return payload

    try:
        payload = asyncio.run(_run())
        self.update_state(state="SUCCESS", meta={"progress": 100, **payload})
        return {"status": "done", "progress": 100, **payload}
    except Exception as exc:
        safe_error = redact_embedding_error(exc)
        _persist_job(
            str(self.request.id),
            status="failed",
            progress=0,
            message="re-embedding failed",
            source_id=source_id,
            result={"source_id": source_id, "source_type": source_type},
            errors=[safe_error],
        )
        self.update_state(state="FAILED", meta={"error": safe_error})
        raise
