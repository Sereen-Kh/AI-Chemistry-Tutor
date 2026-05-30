"""Admin ingestion API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import SessionLocal, get_db
from app.models.textbook import TextbookChunk
from app.schemas.ingestion import (
    IngestionClearResponse,
    IngestionStartRequest,
    IngestionStartResponse,
    IngestionStatsResponse,
    IngestionStatusResponse,
    TestChunkResponse,
)
from app.services.ingestion_pipeline import run_full_ingestion
from app.services.rag import retrieve_context

router = APIRouter(prefix="/admin/ingestion", tags=["admin-ingestion"])

_TASKS: dict[str, dict] = {}


def _update_task(task_id: str, **updates):
    current = _TASKS.setdefault(
        task_id,
        {"task_id": task_id, "status": "pending", "progress": 0, "chunks_created": 0, "pages_processed": 0, "errors": []},
    )
    current.update(updates)


async def _run_ingestion_task(
    task_id: str,
    pdf_path: str,
    chapter_id: int | None,
    clear_existing: bool,
) -> None:
    """Run ingestion in a FastAPI background task for local development."""
    def progress(progress_value: int, message: str) -> None:
        _update_task(task_id, status="processing", progress=progress_value, message=message)

    db = SessionLocal()
    try:
        _update_task(task_id, status="processing", progress=0)
        result = await run_full_ingestion(
            pdf_path,
            chapter_id=chapter_id,
            clear_existing=clear_existing,
            progress_callback=progress,
            db=db,
        )
        _update_task(
            task_id,
            status="done",
            progress=100,
            chunks_created=result["chunks_created"],
            pages_processed=result["pages_processed"],
            errors=result["errors"],
        )
    except Exception as exc:
        _update_task(task_id, status="failed", errors=[str(exc)])
    finally:
        db.close()


@router.post("/start", response_model=IngestionStartResponse)
async def start_ingestion(
    request: IngestionStartRequest,
    background_tasks: BackgroundTasks,
    _admin=Depends(require_admin),
):
    task_id = uuid.uuid4().hex
    _update_task(task_id, status="queued", progress=0)
    background_tasks.add_task(
        _run_ingestion_task,
        task_id,
        request.pdf_path,
        request.chapter_id,
        request.clear_existing,
    )
    return IngestionStartResponse(task_id=task_id, status="queued")


@router.get("/status/{task_id}", response_model=IngestionStatusResponse)
def ingestion_status(task_id: str, _admin=Depends(require_admin)):
    task = _TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/stats", response_model=IngestionStatsResponse)
def ingestion_stats(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_chunks = db.query(func.count(TextbookChunk.id)).scalar() or 0
    avg_chunk_length = db.query(func.avg(func.length(TextbookChunk.content))).scalar() or 0
    pages_processed = (
        db.query(func.count(func.distinct(TextbookChunk.page_number)))
        .filter(TextbookChunk.page_number.isnot(None))
        .scalar()
        or 0
    )
    rows = (
        db.query(TextbookChunk.chapter_id, func.count(TextbookChunk.id))
        .group_by(TextbookChunk.chapter_id)
        .all()
    )
    chunks_by_chapter = {str(chapter_id or "none"): count for chapter_id, count in rows}
    return IngestionStatsResponse(
        total_chunks=total_chunks,
        chunks_by_chapter=chunks_by_chapter,
        avg_chunk_length=float(avg_chunk_length),
        pages_processed=pages_processed,
    )


@router.delete("/clear", response_model=IngestionClearResponse)
def clear_ingestion(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = db.query(TextbookChunk).delete(synchronize_session=False)
    db.commit()
    return IngestionClearResponse(deleted_chunks=deleted)


@router.post("/test-chunk/{chunk_id}", response_model=TestChunkResponse)
async def test_chunk(
    chunk_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    chunk = db.get(TextbookChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    similar = await retrieve_context(db, query=chunk.content, top_k=4)
    return TestChunkResponse(
        chunk={
            "id": chunk.id,
            "content": chunk.content,
            "page_number": chunk.page_number,
            "chapter_id": chunk.chapter_id,
        },
        similar_chunks=[
            {
                "id": item.id,
                "content": item.content,
                "page_number": item.page_number,
                "chapter_id": item.chapter_id,
                "similarity_score": item.similarity_score,
            }
            for item in similar
            if item.id != chunk.id
        ][:3],
    )
