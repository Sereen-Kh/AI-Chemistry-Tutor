"""Homework solver API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.homework import HomeworkResponse, HomeworkSolveImageRequest, HomeworkSolveTextRequest
from app.services import homework_service

router = APIRouter(prefix="/homework", tags=["homework"])


@router.post("/solve-text", response_model=HomeworkResponse)
async def solve_text(
    request: HomeworkSolveTextRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await homework_service.solve_text(db, user_id, request.problem_text, request.topic_id)


@router.post("/solve-image", response_model=HomeworkResponse)
async def solve_image(
    request: HomeworkSolveImageRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await homework_service.solve_image(db, user_id, request.image_path, request.topic_id)


@router.get("/history", response_model=list[HomeworkResponse])
async def homework_history(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_async_db)):
    return await homework_service.list_homework(db, user_id)


@router.get("/{homework_id}", response_model=HomeworkResponse)
async def get_homework(
    homework_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await homework_service.get_homework(db, user_id, homework_id)
