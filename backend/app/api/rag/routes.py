"""RAG retrieval API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.rag import (
    DEFAULT_RAG_MIN_SIMILARITY,
    RagRetrieveDebugRequest,
    RagRetrieveDebugResponse,
    RagRetrieveRequest,
    RagRetrieveResponse,
    RagAnswerRequest,
    RagAnswerResponse,
    RagSearchRequest,
    RagSearchResponse,
    RagSearchResultResponse,
    RagSemanticRetrieveRequest,
    RagSemanticRetrieveResponse,
    RetrievedChunkResponse,
)
from app.services.rag import retrieve_context
from app.services.semantic_rag import SemanticSearchResult, semantic_retrieve_context, semantic_search

router = APIRouter(prefix="/rag", tags=["rag"])


def _chunk_response(item) -> RetrievedChunkResponse:
    return RetrievedChunkResponse(
        id=item.id,
        source_id=item.source_id,
        content=item.content,
        source=item.source,
        source_type=item.source_type,
        content_type=item.content_type,
        page_number=item.page_number,
        unit_id=item.unit_id,
        chapter_id=item.chapter_id,
        lesson_id=item.lesson_id,
        topic_id=item.topic_id,
        metadata_json=item.metadata_json,
        quality_status=item.quality_status,
        quality_warning=item.quality_warning,
        reviewed_metadata_version=item.reviewed_metadata_version,
        curriculum_metadata=item.curriculum_metadata,
        similarity_score=item.similarity_score,
    )


def _search_result_response(item: SemanticSearchResult) -> RagSearchResultResponse:
    return RagSearchResultResponse(
        chunk_id=item.chunk_id,
        source_type=item.source_type,
        score=item.score,
        content=item.content,
        page_start=item.page_start,
        page_end=item.page_end,
        chapter_title=item.chapter_title,
        lesson_title=item.lesson_title,
        chunk_type=item.chunk_type,
        exercise_number=item.exercise_number,
        question_number=item.question_number,
        metadata=item.metadata,
    )


@router.get("/search", response_model=list[RetrievedChunkResponse])
async def search_rag(
    query: str | None = Query(default=None, min_length=1),
    q: str | None = Query(default=None, min_length=1),
    chapter_id: int | None = None,
    unit_id: int | None = None,
    chapter: int | None = None,
    lesson_id: int | None = None,
    lesson: int | None = None,
    topic_id: int | None = None,
    source_types: list[str] | None = Query(default=None),
    content_types: list[str] | None = Query(default=None),
    chunk_type: str | None = Query(default=None),
    page_start: int | None = Query(default=None, ge=1),
    page_end: int | None = Query(default=None, ge=1),
    top_k: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(DEFAULT_RAG_MIN_SIMILARITY, ge=0.0, le=1.0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    resolved_query = query or q
    if not resolved_query:
        raise HTTPException(status_code=422, detail="Provide either 'query' or 'q'.")
    resolved_content_types = content_types or ([chunk_type] if chunk_type else None)
    chunks = await retrieve_context(
        db,
        query=resolved_query,
        user_id=user_id,
        unit_id=unit_id,
        chapter_id=chapter_id if chapter_id is not None else chapter,
        lesson_id=lesson_id if lesson_id is not None else lesson,
        topic_id=topic_id,
        source_types=source_types,
        content_types=resolved_content_types,
        top_k=top_k,
        min_similarity=min_similarity,
        page_start=page_start,
        page_end=page_end,
    )
    return [_chunk_response(item) for item in chunks]


@router.post("/retrieve", response_model=RagRetrieveResponse)
async def retrieve_rag(
    request: RagRetrieveRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    chunks = await retrieve_context(
        db,
        query=request.query,
        user_id=user_id,
        unit_id=request.unit_id,
        chapter_id=request.chapter_id,
        lesson_id=request.lesson_id,
        topic_id=request.topic_id,
        source_types=request.source_types,
        content_types=request.content_types,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        intent=request.intent,
    )
    return RagRetrieveResponse(chunks=[_chunk_response(item) for item in chunks])


@router.post("/search", response_model=RagSearchResponse)
async def search_rag_post(
    request: RagSearchRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    results, diagnostics = await semantic_search(
        db,
        query=request.query,
        source_types=request.source_types,
        top_k=request.top_k,
        filters=request.filters,
        mode=request.mode,
        user_id=user_id,
        intent=request.intent,
        min_similarity=request.min_similarity,
    )
    return RagSearchResponse(
        query=request.query,
        mode=request.mode,
        results=[_search_result_response(item) for item in results],
        diagnostics=diagnostics,
    )


@router.post("/answer", response_model=RagAnswerResponse)
async def answer_rag(
    request: RagAnswerRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    results, diagnostics = await semantic_search(
        db,
        query=request.query,
        source_types=request.source_types,
        top_k=request.top_k,
        filters=request.filters,
        mode=request.mode,
        user_id=user_id,
        intent=request.intent,
        min_similarity=request.min_similarity,
    )
    if not results:
        return RagAnswerResponse(
            answer="لم أجد مقاطع كافية في المصادر المفهرسة للإجابة بثقة.",
            sources=[],
            confidence=0.0,
            diagnostics=diagnostics,
        )
    best = results[0]
    answer = (
        "أقرب مقطع وجدته في المصادر المفهرسة:\n\n"
        f"{best.content}\n\n"
        f"المصدر: {best.source_type}، الصفحة {best.page_start}."
    )
    return RagAnswerResponse(
        answer=answer,
        sources=[_search_result_response(item) for item in results],
        confidence=max(item.score for item in results),
        diagnostics=diagnostics,
    )


@router.post("/semantic-retrieve", response_model=RagSemanticRetrieveResponse)
async def semantic_retrieve_rag(
    request: RagSemanticRetrieveRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    result = await semantic_retrieve_context(
        db,
        request.query,
        user_id=user_id,
        source_types=request.source_types,
        unit_id=request.unit_id,
        chapter_id=request.chapter_id,
        lesson_id=request.lesson_id,
        topic_id=request.topic_id,
        top_k=request.top_k,
        intent=request.intent,
    )
    quality_gate = result.diagnostics.get("quality_gate")
    return RagSemanticRetrieveResponse(
        chunks=[_chunk_response(item) for item in result.chunks],
        diagnostics=result.diagnostics,
        quality_gate=quality_gate if isinstance(quality_gate, dict) else None,
    )


@router.post("/retrieve-debug", response_model=RagRetrieveDebugResponse)
async def retrieve_rag_debug(
    request: RagRetrieveDebugRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    diagnostics: dict = {}
    chunks = await retrieve_context(
        db,
        query=request.query,
        user_id=user_id,
        unit_id=request.unit_id,
        chapter_id=request.chapter_id,
        lesson_id=request.lesson_id,
        topic_id=request.topic_id,
        source_types=request.source_types,
        content_types=request.content_types,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        intent=request.intent,
        diagnostics_callback=diagnostics.update,
    )
    return RagRetrieveDebugResponse(chunks=[_chunk_response(item) for item in chunks], diagnostics=diagnostics)
