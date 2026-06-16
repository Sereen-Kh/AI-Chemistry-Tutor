"""Guided interactive chemistry solver API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_async_db
from app.models.user import User
from app.schemas.interactive_solver import (
    InteractiveAnswerResponse,
    InteractiveAnswerSubmit,
    InteractiveSessionCreate,
    InteractiveSessionResponse,
    InteractiveSessionSummaryResponse,
)
from app.services import interactive_solver_service

router = APIRouter(prefix="/interactive-solver", tags=["interactive-solver"])


@router.post("/sessions", response_model=InteractiveSessionResponse, status_code=201)
async def create_interactive_session(
    request: InteractiveSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await interactive_solver_service.start_interactive_session(db, user, request)


@router.get("/sessions", response_model=list[InteractiveSessionResponse])
async def list_interactive_sessions(
    status: str | None = Query(default=None, pattern="^(active|completed|abandoned)$"),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await interactive_solver_service.list_interactive_sessions(db, user, status=status, limit=limit)


@router.get("/sessions/{session_id}", response_model=InteractiveSessionResponse)
async def get_interactive_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await interactive_solver_service.get_interactive_session(db, user, session_id)


@router.post("/sessions/{session_id}/answer", response_model=InteractiveAnswerResponse)
async def submit_interactive_answer(
    session_id: int,
    request: InteractiveAnswerSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await interactive_solver_service.submit_step_answer(db, user, session_id, request)


@router.post("/sessions/{session_id}/hint", response_model=InteractiveAnswerResponse)
async def get_interactive_hint(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await interactive_solver_service.get_step_hint(db, user, session_id)


@router.post("/sessions/{session_id}/finish", response_model=InteractiveSessionSummaryResponse)
async def finish_interactive_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await interactive_solver_service.finish_interactive_session(db, user, session_id)
