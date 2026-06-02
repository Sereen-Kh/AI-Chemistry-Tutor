"""Flashcard API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, require_admin
from app.database import get_async_db
from app.schemas.flashcards import (
    FlashcardCreateRequest,
    FlashcardProgressResponse,
    FlashcardResponse,
    FlashcardReviewRequest,
)
from app.services import flashcard_service

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("", response_model=list[FlashcardResponse])
async def list_flashcards(topic_id: int | None = Query(default=None), db: AsyncSession = Depends(get_async_db)):
    return await flashcard_service.list_flashcards(db, topic_id=topic_id)


@router.post("", response_model=FlashcardResponse, status_code=201)
async def create_flashcard(
    request: FlashcardCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    return await flashcard_service.create_flashcard(db, request.model_dump())


@router.post("/{flashcard_id}/review", response_model=FlashcardProgressResponse)
async def review_flashcard(
    flashcard_id: int,
    request: FlashcardReviewRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await flashcard_service.review_flashcard(db, user_id, flashcard_id, request.quality)
