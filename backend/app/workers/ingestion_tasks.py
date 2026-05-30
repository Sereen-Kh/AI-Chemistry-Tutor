"""Celery tasks for PDF ingestion."""

from __future__ import annotations

import asyncio

from app.services.ingestion_pipeline import run_full_ingestion
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="ingest_pdf")
def ingest_pdf_task(self, pdf_path: str, chapter_id: int | None = None, clear_existing: bool = False):
    """Run the full PDF ingestion pipeline and report progress to Celery."""
    def progress(value: int, message: str) -> None:
        self.update_state(state="PROCESSING", meta={"progress": value, "message": message})

    try:
        result = asyncio.run(
            run_full_ingestion(
                pdf_path,
                chapter_id=chapter_id,
                clear_existing=clear_existing,
                progress_callback=progress,
            )
        )
        return {"status": "done", "progress": 100, **result}
    except Exception as exc:
        self.update_state(state="FAILED", meta={"error": str(exc)})
        raise
