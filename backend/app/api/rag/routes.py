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
    top_k: int = Query(5, ge=1, le=20),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _ = user_id
    return await retrieve_context(db, query=query, chapter_id=chapter_id, top_k=top_k)
