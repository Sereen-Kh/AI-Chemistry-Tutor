"""Progress service functions."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement
from app.models.chemistry import LessonProgress
from app.models.user_progress import UserProgress


async def update_lesson_progress(db: AsyncSession, user_id: int, lesson_id: int, status: str) -> LessonProgress:
    result = await db.execute(
        select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        record = LessonProgress(user_id=user_id, lesson_id=lesson_id, status=status)
        db.add(record)
    else:
        record.status = status
    if status == "completed":
        record.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(record)
    return record


async def list_user_progress(db: AsyncSession, user_id: int) -> list[UserProgress]:
    result = await db.execute(select(UserProgress).where(UserProgress.user_id == user_id))
    return list(result.scalars().all())


async def list_achievements(db: AsyncSession, user_id: int) -> list[Achievement]:
    result = await db.execute(select(Achievement).where(Achievement.user_id == user_id))
    return list(result.scalars().all())


async def get_lesson_progress(db: AsyncSession, user_id: int, lesson_id: int) -> LessonProgress:
    result = await db.execute(
        select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Lesson progress not found")
    return record
