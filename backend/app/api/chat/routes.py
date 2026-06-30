"""Chat API routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
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


def _csv_values(value: str | None) -> list[str] | None:
    if not value:
        return None
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or None


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
        answer_scope=request.answer_scope,
        source_types=request.source_types,
        teaching_style=request.teaching_style,
        teaching_level=request.teaching_level.value if request.teaching_level else None,
        explanation_method=request.explanation_method.value if request.explanation_method else None,
        learning_modes=[mode.value for mode in request.learning_modes] if request.learning_modes else None,
        student_interests=[interest.value for interest in request.student_interests] if request.student_interests else None,
        action=request.action,
    )


@router.post("/messages", response_model=MessageResponse)
async def send_unified_chat_message(
    conversation_id: str = Form(..., alias="conversationId"),
    lesson_id: str | None = Form(None, alias="lessonId"),
    text: str | None = Form(None),
    requested_return_type: str = Form("auto", alias="requestedReturnType"),
    language: str = Form("auto"),
    answer_scope: str = Form("auto", alias="answerScope"),
    teaching_style: str | None = Form(None, alias="teachingStyle"),
    teaching_level: str | None = Form(None, alias="teachingLevel"),
    explanation_method: str | None = Form(None, alias="explanationMethod"),
    learning_modes: str | None = Form(None, alias="learningModes"),
    student_interests: str | None = Form(None, alias="studentInterests"),
    action: str | None = Form(None),
    audio: UploadFile | None = File(None),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Unified multipart text/audio chat endpoint for Ask AI."""
    try:
        session_id = int(conversation_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CONVERSATION_ID", "message": "conversationId must be a chat session id."}) from exc

    _ = lesson_id
    audio_bytes = await audio.read() if audio is not None else None
    return await chat_service.send_multimodal_message(
        db,
        session_id=session_id,
        user_id=user_id,
        text=text,
        audio_bytes=audio_bytes,
        audio_filename=audio.filename if audio else None,
        audio_content_type=audio.content_type if audio else None,
        requested_return_type=requested_return_type,
        language=language,
        answer_scope=answer_scope,
        source_types=None,
        teaching_style=teaching_style,
        teaching_level=teaching_level,
        explanation_method=explanation_method,
        learning_modes=_csv_values(learning_modes),
        student_interests=_csv_values(student_interests),
        action=action,
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
        conversation_id=request.conversation_id,
        parent_message_id=request.parent_message_id,
        teaching_style=request.teaching_style,
        teaching_level=request.teaching_level.value if request.teaching_level else None,
        explanation_method=request.explanation_method.value if request.explanation_method else None,
        learning_modes=[mode.value for mode in request.learning_modes] if request.learning_modes else None,
        student_interests=[interest.value for interest in request.student_interests] if request.student_interests else None,
        action=request.action,
        previous_question=request.previous_question,
        previous_answer=request.previous_answer,
        previous_sources=request.previous_sources,
        previous_selected_chunks=request.previous_selected_chunks,
    )
    return ChatAnswerResponse(
        answer=result["answer"],
        answer_text=result.get("answer_text", result["answer"]),
        answer_type=result["answer_type"],
        route=result.get("route", "textbook_rag"),
        grounding=result.get("grounding", "book"),
        answer_scope=result.get("answer_scope", request.answer_scope),
        teaching_level=result.get("teaching_level", "standard"),
        explanation_method=result.get("explanation_method", "direct"),
        learning_modes=result.get("learning_modes", ["text"]),
        student_interests=result.get("student_interests", []),
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
        citations=result.get("citations", []),
        media_blocks=[AnswerBlock(**block) for block in result.get("media_blocks", [])],
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
