"""Lesson API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.database import get_async_db
from app.schemas.lessons import LessonCreateRequest, LessonResponse, LessonUpdateRequest
from app.services import curriculum_service

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("", response_model=list[LessonResponse])
async def list_lessons(
    chapter_id: int | None = Query(default=None),
    semester: int | None = Query(default=None, ge=1, le=2),
    db: AsyncSession = Depends(get_async_db),
):
    return await curriculum_service.list_lessons(db, chapter_id=chapter_id, semester=semester)


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(lesson_id: int, db: AsyncSession = Depends(get_async_db)):
    return await curriculum_service.get_lesson(db, lesson_id)


@router.post("", response_model=LessonResponse, status_code=201)
async def create_lesson(
    request: LessonCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    return await curriculum_service.create_lesson(db, request.model_dump())


@router.patch("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    request: LessonUpdateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    return await curriculum_service.update_lesson(db, lesson_id, request.model_dump(exclude_unset=True))
