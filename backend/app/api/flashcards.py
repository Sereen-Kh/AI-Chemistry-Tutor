"""Flashcard API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, require_admin
from app.database import get_async_db
from app.schemas.flashcards import (
    FlashcardCreateRequest,
    FlashcardDueResponse,
    FlashcardGenerateRequest,
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


@router.post("/generate", response_model=list[FlashcardResponse], status_code=201)
async def generate_flashcards(
    request: FlashcardGenerateRequest,
    _user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await flashcard_service.generate_flashcards(db, request)


@router.get("/due", response_model=list[FlashcardDueResponse])
async def due_flashcards(
    limit: int = Query(default=30, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    rows = await flashcard_service.due_flashcards(db, user_id, limit=limit)
    return [
        FlashcardDueResponse(
            id=card.id,
            topic_id=card.topic_id,
            front_ar=card.front_ar,
            back_ar=card.back_ar,
            created_by=card.created_by,
            mastered=progress.mastered if progress else False,
            review_count=progress.review_count if progress else 0,
            ease_factor=progress.ease_factor if progress else 2.5,
            interval_days=progress.interval_days if progress else 0,
            next_review_at=progress.next_review_at if progress else None,
            last_reviewed=progress.last_reviewed if progress else None,
        )
        for card, progress in rows
    ]


@router.post("/{flashcard_id}/review", response_model=FlashcardProgressResponse)
async def review_flashcard(
    flashcard_id: int,
    request: FlashcardReviewRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await flashcard_service.review_flashcard(db, user_id, flashcard_id, request.quality)
