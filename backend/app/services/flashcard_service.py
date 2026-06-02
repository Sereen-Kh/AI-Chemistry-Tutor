"""Flashcard service functions."""

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcard import Flashcard, FlashcardProgress


async def list_flashcards(db: AsyncSession, topic_id: int | None = None) -> list[Flashcard]:
    stmt = select(Flashcard)
    if topic_id is not None:
        stmt = stmt.where(Flashcard.topic_id == topic_id)
    result = await db.execute(stmt.order_by(Flashcard.id))
    return list(result.scalars().all())


async def create_flashcard(db: AsyncSession, data: dict) -> Flashcard:
    card = Flashcard(**data)
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


async def review_flashcard(db: AsyncSession, user_id: int, flashcard_id: int, quality: int) -> FlashcardProgress:
    card = await db.get(Flashcard, flashcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    result = await db.execute(
        select(FlashcardProgress).where(
            FlashcardProgress.user_id == user_id,
            FlashcardProgress.flashcard_id == flashcard_id,
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = FlashcardProgress(user_id=user_id, flashcard_id=flashcard_id)
        db.add(progress)
    progress.review_count += 1
    progress.mastered = quality >= 4
    progress.interval_days = max(1, quality * 2)
    progress.next_review_at = date.today() + timedelta(days=progress.interval_days)
    progress.last_reviewed = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(progress)
    return progress
