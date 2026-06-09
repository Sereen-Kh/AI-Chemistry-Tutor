"""RAG retrieval API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.rag import (
    DEFAULT_RAG_MIN_SIMILARITY,
    RagRetrieveDebugRequest,
    RagRetrieveDebugResponse,
    RagRetrieveRequest,
    RagRetrieveResponse,
    RagSemanticRetrieveRequest,
    RagSemanticRetrieveResponse,
    RetrievedChunkResponse,
)
from app.services.rag import retrieve_context
from app.services.semantic_rag import semantic_retrieve_context

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
        chapter_id=item.chapter_id,
        lesson_id=item.lesson_id,
        topic_id=item.topic_id,
        metadata_json=item.metadata_json,
        similarity_score=item.similarity_score,
    )


@router.get("/search", response_model=list[RetrievedChunkResponse])
async def search_rag(
    query: str = Query(..., min_length=1),
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    source_types: list[str] | None = Query(default=None),
    content_types: list[str] | None = Query(default=None),
    top_k: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(DEFAULT_RAG_MIN_SIMILARITY, ge=0.0, le=1.0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    chunks = await retrieve_context(
        db,
        query=query,
        user_id=user_id,
        chapter_id=chapter_id,
        lesson_id=lesson_id,
        topic_id=topic_id,
        source_types=source_types,
        content_types=content_types,
        top_k=top_k,
        min_similarity=min_similarity,
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
