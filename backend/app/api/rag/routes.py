"""RAG retrieval API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.database import get_db
from app.schemas.rag import RagRetrieveRequest, RagRetrieveResponse, RetrievedChunkResponse
from app.services.rag import retrieve_context

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
    min_similarity: float = Query(0.0, ge=-1.0, le=1.0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    )
    return RagRetrieveResponse(chunks=[_chunk_response(item) for item in chunks])
