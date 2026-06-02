"""Progress and achievement API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.progress import (
    AchievementResponse,
    LessonProgressResponse,
    LessonProgressUpdateRequest,
    UserProgressResponse,
)
from app.services import progress_service

router = APIRouter(prefix="/progress", tags=["progress"])


@router.put("/lessons/{lesson_id}", response_model=LessonProgressResponse)
async def update_lesson_progress(
    lesson_id: int,
    request: LessonProgressUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await progress_service.update_lesson_progress(db, user_id, lesson_id, request.status)


@router.get("/topics", response_model=list[UserProgressResponse])
async def topic_progress(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_async_db)):
    return await progress_service.list_user_progress(db, user_id)


@router.get("/achievements", response_model=list[AchievementResponse])
async def achievements(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_async_db)):
    return await progress_service.list_achievements(db, user_id)
