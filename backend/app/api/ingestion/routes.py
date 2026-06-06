"""Admin ingestion API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import SessionLocal, get_db
from app.models.ingestion import IngestionJob, IngestionPage
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk
from app.schemas.ingestion import (
    ExtractedQuestionResponse,
    IngestionClearResponse,
    IngestionPageResponse,
    IngestionRebuildCacheRequest,
    IngestionRebuildCacheResponse,
    IngestionRetryPageResponse,
    IngestionStartRequest,
    IngestionStartResponse,
    IngestionStatsResponse,
    IngestionStatusResponse,
    IngestionTestQueryRequest,
    IngestionTestQueryResponse,
    QuestionReviewRequest,
    SourceDeleteResponse,
    SourceRegisterRequest,
    SourceResponse,
    TestChunkResponse,
)
from app.services.ingestion_pipeline import run_full_ingestion
from app.services.rag import retrieve_context
from app.services.rag_rebuild import rebuild_rag_chunks_from_cached_pages

router = APIRouter(prefix="/admin/ingestion", tags=["admin-ingestion"])

_TASKS: dict[str, dict] = {}


def _update_task(task_id: str, **updates):
    current = _TASKS.setdefault(
        task_id,
        {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "chunks_created": 0,
            "pages_processed": 0,
            "errors": [],
        },
    )
    current.update(updates)


async def _run_ingestion_task(
    task_id: str,
    pdf_path: str,
    title: str | None,
    source_type: str,
    grade: str,
    subject: str,
    year: int | None,
    max_pages: int | None,
    ocr_provider: str | None,
    ingestion_mode: str | None,
    ocr_required_for_vision: bool | None,
    allow_partial_ingestion: bool | None,
    chapter_id: int | None,
    lesson_id: int | None,
    topic_id: int | None,
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
            lesson_id=lesson_id,
            topic_id=topic_id,
            source_type=source_type,
            title=title,
            grade=grade,
            subject=subject,
            year=year,
            max_pages=max_pages,
            ocr_provider_name=ocr_provider,
            ingestion_mode=ingestion_mode,
            ocr_required_for_vision=ocr_required_for_vision,
            allow_partial_ingestion=allow_partial_ingestion,
            clear_existing=clear_existing,
            progress_callback=progress,
            db=db,
        )
        job = db.query(IngestionJob).filter(IngestionJob.job_uid == task_id).first()
        if job:
            job.source_id = result["source_id"]
            job.status = result["status"]
            job.progress = 100
            job.message = "ingestion finished"
            job.result_json = result
            job.errors_json = result["errors"]
            db.query(IngestionPage).filter(IngestionPage.source_id == result["source_id"]).delete(
                synchronize_session=False
            )
            for page in result["page_statuses"]:
                db.add(
                    IngestionPage(
                        source_id=result["source_id"],
                        job_id=job.id,
                        page_number=page["page_number"],
                        page_type=page["page_type"],
                        status=page["status"],
                        extraction_methods=[page.get("extraction_method")],
                        char_count=page.get("char_count") or 0,
                        completeness_score=page.get("completeness_score") or 0.0,
                        content_preview=None,
                    )
                )
            db.commit()
        _update_task(
            task_id,
            status="done" if result["status"] != "failed" else "failed",
            progress=100,
            source_id=result["source_id"],
            source_status=result["status"],
            total_pages=result["total_pages"],
            pages_to_process=result["pages_to_process"],
            selectable_text_pages=result["selectable_text_pages"],
            needs_vision_pages=result["needs_vision_pages"],
            mixed_vision_pages=result["mixed_vision_pages"],
            chunks_created=result["chunks_created"],
            questions_extracted=result["questions_extracted"],
            diagrams_extracted=result["diagrams_extracted"],
            tables_extracted=result["tables_extracted"],
            equations_extracted=result["equations_extracted"],
            pages_processed=result["pages_processed"],
            pages_completed=result["pages_completed"],
            pages_failed=result["pages_failed"],
            pages_skipped_dry_run=result["pages_skipped_dry_run"],
            failed_pages=result["failed_pages"],
            skipped_dry_run_pages=result["skipped_dry_run_pages"],
            page_statuses=result["page_statuses"],
            ocr_provider=result["ocr_provider"],
            ocr_provider_configured=result["ocr_provider_configured"],
            vision_provider=result["vision_provider"],
            vision_provider_configured=result["vision_provider_configured"],
            ingestion_mode=result["ingestion_mode"],
            ocr_required_for_vision=result["ocr_required_for_vision"],
            allow_partial_ingestion=result["allow_partial_ingestion"],
            warnings=result["warnings"],
            errors=result["errors"],
        )
    except Exception as exc:
        job = db.query(IngestionJob).filter(IngestionJob.job_uid == task_id).first()
        if job:
            job.status = "failed"
            job.errors_json = [str(exc)]
            db.commit()
        _update_task(task_id, status="failed", errors=[str(exc)])
    finally:
        db.close()


@router.post("/start", response_model=IngestionStartResponse)
async def start_ingestion(
    request: IngestionStartRequest,
    background_tasks: BackgroundTasks,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    task_id = uuid.uuid4().hex
    db.add(IngestionJob(job_uid=task_id, status="queued", progress=0, message="queued"))
    db.commit()
    _update_task(task_id, status="queued", progress=0)
    background_tasks.add_task(
        _run_ingestion_task,
        task_id,
        request.pdf_path,
        request.title,
        request.source_type,
        request.grade,
        request.subject,
        request.year,
        request.max_pages,
        request.ocr_provider,
        request.ingestion_mode,
        request.ocr_required_for_vision,
        request.allow_partial_ingestion,
        request.chapter_id,
        request.lesson_id,
        request.topic_id,
        request.clear_existing,
    )
    return IngestionStartResponse(task_id=task_id, status="queued")


@router.post("/rebuild-from-cache", response_model=IngestionRebuildCacheResponse)
async def rebuild_from_cache(
    request: IngestionRebuildCacheRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    result = await rebuild_rag_chunks_from_cached_pages(
        db,
        cache_dir=request.cache_dir,
        title=request.title,
        source_type=request.source_type,
        grade=request.grade,
        subject=request.subject,
        year=request.year,
        file_path=request.file_path,
        chapter_id=request.chapter_id,
        lesson_id=request.lesson_id,
        topic_id=request.topic_id,
        clear_existing=request.clear_existing,
    )
    return IngestionRebuildCacheResponse(**result.to_dict())


@router.get("/sources", response_model=list[SourceResponse])
def list_sources(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(ContentSource).order_by(ContentSource.created_at.desc()).all()


@router.post("/sources", response_model=SourceResponse, status_code=201)
def register_source(
    request: SourceRegisterRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    source = ContentSource(
        source_type=request.source_type,
        title=request.title,
        grade=request.grade,
        subject=request.subject,
        year=request.year,
        file_path=request.file_path,
        original_filename=request.original_filename,
        status="pending",
        metadata_json=request.metadata_json,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/sources/{source_id}", response_model=SourceResponse)
def get_source(
    source_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    source = db.get(ContentSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


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
    total_sources = db.query(func.count(ContentSource.id)).scalar() or 0
    total_chunks = db.query(func.count(RagChunk.id)).scalar() or 0
    total_questions = db.query(func.count(ExtractedQuestion.id)).scalar() or 0
    unreviewed_questions = (
        db.query(func.count(ExtractedQuestion.id)).filter(ExtractedQuestion.needs_review.is_(True)).scalar() or 0
    )
    reviewed_questions = total_questions - unreviewed_questions
    avg_chunk_length = db.query(func.avg(func.length(RagChunk.content))).scalar() or 0
    pages_processed = (
        db.query(func.count(func.distinct(RagChunk.page_number)))
        .filter(RagChunk.page_number.isnot(None))
        .scalar()
        or 0
    )
    rows = (
        db.query(RagChunk.chapter_id, func.count(RagChunk.id))
        .group_by(RagChunk.chapter_id)
        .all()
    )
    chunks_by_chapter = {str(chapter_id or "none"): count for chapter_id, count in rows}
    source_type_rows = (
        db.query(RagChunk.source_type, func.count(RagChunk.id))
        .group_by(RagChunk.source_type)
        .all()
    )
    chunks_by_source_type = {source_type or "unknown": count for source_type, count in source_type_rows}
    return IngestionStatsResponse(
        total_chunks=total_chunks,
        total_sources=total_sources,
        total_questions=total_questions,
        reviewed_questions=reviewed_questions,
        unreviewed_questions=unreviewed_questions,
        chunks_by_chapter=chunks_by_chapter,
        chunks_by_source_type=chunks_by_source_type,
        avg_chunk_length=float(avg_chunk_length),
        pages_processed=pages_processed,
    )


@router.delete("/clear", response_model=IngestionClearResponse)
def clear_ingestion(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = db.query(RagChunk).delete(synchronize_session=False)
    db.commit()
    return IngestionClearResponse(deleted_chunks=deleted)


@router.delete("/source/{source_id}", response_model=SourceDeleteResponse)
def delete_source(
    source_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    source = db.get(ContentSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    deleted_chunks = db.query(RagChunk).filter(RagChunk.source_id == source_id).count()
    deleted_questions = db.query(ExtractedQuestion).filter(ExtractedQuestion.source_id == source_id).count()
    db.delete(source)
    db.commit()
    return SourceDeleteResponse(
        deleted_source_id=source_id,
        deleted_chunks=deleted_chunks,
        deleted_questions=deleted_questions,
    )


@router.delete("/sources/{source_id}", response_model=SourceDeleteResponse)
def delete_source_plural(
    source_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return delete_source(source_id, _admin, db)


@router.get("/pages/{source_id}", response_model=list[IngestionPageResponse])
def list_ingestion_pages(
    source_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(IngestionPage)
        .filter(IngestionPage.source_id == source_id)
        .order_by(IngestionPage.page_number.asc())
        .all()
    )


@router.post("/retry-page/{page_id}", response_model=IngestionRetryPageResponse)
def retry_ingestion_page(
    page_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    page = db.get(IngestionPage, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Ingestion page not found")
    page.status = "queued_retry"
    db.commit()
    return IngestionRetryPageResponse(
        page_id=page_id,
        status=page.status,
        message="Page marked for retry. Full per-page retry worker is not implemented yet.",
    )


@router.post("/test-query", response_model=IngestionTestQueryResponse)
async def test_query(
    request: IngestionTestQueryRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    chunks = await retrieve_context(db, query=request.query, top_k=request.top_k)
    return IngestionTestQueryResponse(
        query=request.query,
        chunks=[
            {
                "id": chunk.id,
                "source_id": chunk.source_id,
                "source": chunk.source,
                "page_number": chunk.page_number,
                "content_type": chunk.content_type,
                "similarity_score": chunk.similarity_score,
                "content": chunk.content,
            }
            for chunk in chunks
        ],
    )


@router.post("/test-chunk/{chunk_id}", response_model=TestChunkResponse)
async def test_chunk(
    chunk_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    chunk = db.get(RagChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    similar = await retrieve_context(db, query=chunk.content, top_k=4)
    return TestChunkResponse(
        chunk={
            "id": chunk.id,
            "source_id": chunk.source_id,
            "content": chunk.content,
            "page_number": chunk.page_number,
            "chapter_id": chunk.chapter_id,
            "content_type": chunk.content_type,
            "source_type": chunk.source_type,
        },
        similar_chunks=[
            {
                "id": item.id,
                "source_id": item.source_id,
                "content": item.content,
                "page_number": item.page_number,
                "chapter_id": item.chapter_id,
                "content_type": item.content_type,
                "source_type": item.source_type,
                "similarity_score": item.similarity_score,
            }
            for item in similar
            if item.id != chunk.id
        ][:3],
    )


@router.get("/questions/unreviewed", response_model=list[ExtractedQuestionResponse])
def list_unreviewed_questions(
    limit: int = 50,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(ExtractedQuestion)
        .filter(ExtractedQuestion.needs_review.is_(True))
        .order_by(ExtractedQuestion.created_at.asc())
        .limit(limit)
        .all()
    )


@router.post("/questions/{question_id}/review", response_model=ExtractedQuestionResponse)
def review_question(
    question_id: int,
    request: QuestionReviewRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    question = db.get(ExtractedQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    for field in [
        "question_text",
        "question_type",
        "options",
        "correct_answer",
        "explanation",
        "answer_source",
        "difficulty",
        "needs_review",
    ]:
        value = getattr(request, field)
        if value is not None or field == "needs_review":
            setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question
