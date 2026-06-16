"""Celery tasks for RAG maintenance jobs."""

from __future__ import annotations

import asyncio

from app.database import AsyncSessionLocal
from app.services.rag_cache import invalidate_rag_caches
from app.services.rag_reembed import reembed_rag_chunks
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="reembed_rag_chunks")
def reembed_rag_chunks_task(
    self,
    source_id: int | None = None,
    source_type: str | None = None,
    batch_size: int = 50,
    dry_run: bool = False,
    force: bool = True,
    resume_failed: bool = False,
):
    """Re-embed RAG chunks with the configured production embedding model."""

    async def _run() -> dict:
        self.update_state(state="PROCESSING", meta={"progress": 0, "message": "re-embedding started"})

        def update_progress(payload: dict) -> None:
            self.update_state(state="PROCESSING", meta=payload)

        async with AsyncSessionLocal() as db:
            result = await reembed_rag_chunks(
                db,
                source_id=source_id,
                source_type=source_type,
                batch_size=batch_size,
                dry_run=dry_run,
                force=force,
                resume_failed=resume_failed,
                progress_callback=update_progress,
            )
            payload = result.to_dict()
            payload["cache_invalidation"] = await invalidate_rag_caches()
            return payload

    try:
        payload = asyncio.run(_run())
        self.update_state(state="SUCCESS", meta={"progress": 100, **payload})
        return {"status": "done", "progress": 100, **payload}
    except Exception as exc:
        self.update_state(state="FAILED", meta={"error": str(exc)})
        raise
