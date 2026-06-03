"""Chat API routes."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.chat import (
    AnswerBlock,
    AnswerSourceBlock,
    ChatAnswerResponse,
    ChatAskRequest,
    ChatSourceResponse,
    MessageFeedbackRequest,
    MessageResponse,
    SendMessageRequest,
    SessionCreate,
    SessionResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_chat_session(
    request: SessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
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
    db: AsyncSession = Depends(get_async_db),
):
    return await chat_service.get_user_sessions(db, user_id)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_chat_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await chat_service.get_owned_session(db, session_id, user_id)


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_chat_message(
    session_id: int,
    request: SendMessageRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await chat_service.send_message(
        db,
        session_id=session_id,
        user_id=user_id,
        content=request.content,
        message_format=request.format,
    )


@router.post("/ask", response_model=ChatAnswerResponse)
async def ask_chat(
    request: ChatAskRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    result = await chat_service.ask_question(
        db,
        user_id=user_id,
        question=request.question,
        lesson_id=request.lesson_id,
        topic_id=request.topic_id,
        source_types=request.source_types,
        preferred_answer_type=request.preferred_answer_type,
        answer_scope=request.answer_scope,
    )
    return ChatAnswerResponse(
        answer=result["answer"],
        answer_type=result["answer_type"],
        route=result.get("route", "textbook_rag"),
        grounding=result.get("grounding", "book"),
        answer_scope=result.get("answer_scope", request.answer_scope),
        blocks=[AnswerBlock(**block) for block in result["blocks"]],
        sources=[
            ChatSourceResponse(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                source=chunk.source,
                page_number=chunk.page_number,
                content_type=chunk.content_type,
                similarity_score=chunk.similarity_score,
            )
            for chunk in result["sources"]
        ],
        source_blocks=[AnswerSourceBlock(**block) for block in result.get("source_blocks", [])],
        page_numbers=result["page_numbers"],
        confidence=result["confidence"],
        diagnostics=result.get("diagnostics", {}),
        suggested_next_action=result["suggested_next_action"],
    )


@router.post("/messages/{message_id}/feedback", response_model=MessageResponse)
async def message_feedback(
    message_id: int,
    request: MessageFeedbackRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await chat_service.update_message_feedback(db, message_id, user_id, request.feedback)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await chat_service.delete_session(db, session_id, user_id)
    return Response(status_code=204)
