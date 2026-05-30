"""Chat API routes."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.database import get_db
from app.schemas.chat import MessageResponse, SendMessageRequest, SessionCreate, SessionResponse
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_chat_session(
    request: SessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return await chat_service.create_session(
        db,
        user_id=user_id,
        title=request.title or "محادثة جديدة",
        lesson_id=request.lesson_id,
        style=request.style,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_chat_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return await chat_service.get_user_sessions(db, user_id)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_chat_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return chat_service.get_owned_session(db, session_id, user_id)


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_chat_message(
    session_id: int,
    request: SendMessageRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return await chat_service.send_message(
        db,
        session_id=session_id,
        user_id=user_id,
        content=request.content,
        message_format=request.format,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await chat_service.delete_session(db, session_id, user_id)
    return Response(status_code=204)
