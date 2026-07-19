"""Authenticated persistent Study Session routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.study_sessions import StudySessionCreate, StudySessionResponse
from app.services import study_session_service


router = APIRouter(prefix="/study-sessions", tags=["study_sessions"])


@router.post("", response_model=StudySessionResponse, status_code=201)
async def start_study_session(
    request: StudySessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.start_study_session(db, user_id, request)


@router.get("/current", response_model=StudySessionResponse | None)
async def get_current_study_session(
    lesson_id: int | None = Query(default=None, gt=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.get_current_session(db, user_id, lesson_id=lesson_id)


@router.get("", response_model=list[StudySessionResponse])
async def list_study_sessions(
    status: str | None = Query(default=None, pattern="^(running|paused|completed|abandoned)$"),
    lesson_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.list_study_sessions(
        db,
        user_id,
        status=status,
        lesson_id=lesson_id,
        limit=limit,
    )


@router.get("/{session_id}", response_model=StudySessionResponse)
async def get_study_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.get_study_session(db, user_id, session_id)


@router.post("/{session_id}/heartbeat", response_model=StudySessionResponse)
async def heartbeat_study_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.heartbeat_study_session(db, user_id, session_id)


@router.post("/{session_id}/pause", response_model=StudySessionResponse)
async def pause_study_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.pause_study_session(db, user_id, session_id)


@router.post("/{session_id}/resume", response_model=StudySessionResponse)
async def resume_study_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.resume_study_session(db, user_id, session_id)


@router.post("/{session_id}/complete", response_model=StudySessionResponse)
async def complete_study_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.complete_study_session(db, user_id, session_id)


@router.post("/{session_id}/abandon", response_model=StudySessionResponse)
async def abandon_study_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_session_service.abandon_study_session(db, user_id, session_id)
