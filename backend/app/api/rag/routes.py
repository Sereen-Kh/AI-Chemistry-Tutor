"""RAG retrieval API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.database import get_db
from app.schemas.rag import RetrievedChunkResponse
from app.services.rag import retrieve_context

router = APIRouter(prefix="/rag", tags=["rag"])


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
    return await retrieve_context(
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
