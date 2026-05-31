"""Chat orchestration service."""

from __future__ import annotations

import time

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.services import ai_service
from app.services.rag import format_context, retrieve_context


async def create_session(
    db: Session,
    user_id: int,
    title: str = "محادثة جديدة",
    lesson_id: int | None = None,
    style: str | None = None,
) -> ChatSession:
    """Create a new chat session for a user."""
    session = ChatSession(user_id=user_id, title=title, lesson_id=lesson_id, style=style)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def get_user_sessions(db: Session, user_id: int) -> list[ChatSession]:
    """Return all chat sessions for a user."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


def get_owned_session(db: Session, session_id: int, user_id: int) -> ChatSession:
    """Load a chat session and verify the current user owns it."""
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


async def send_message(
    db: Session,
    session_id: int,
    user_id: int,
    content: str,
    message_format: str = "text",
) -> ChatMessage:
    """Save a user message, retrieve RAG context, generate and save an AI reply."""
    session = get_owned_session(db, session_id, user_id)
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=content,
        format=message_format,
    )
    db.add(user_message)
    db.flush()

    chunks = await retrieve_context(db, content, user_id=user_id, top_k=6, min_similarity=0.0)
    context = format_context(chunks)
    system_prompt = (
        "أجب بالعربية. إذا لم تكن الإجابة موجودة في مصادر الكتاب أو الامتحانات "
        "المتاحة، قل بوضوح إنك لم تجدها في المصادر المتاحة، ثم يمكنك تقديم شرح عام منفصل."
    )
    if context:
        system_prompt = (
            "استخدم المقاطع التالية من كتاب الكيمياء للصف التاسع أساساً للإجابة. "
            "اذكر رقم الصفحة أو المصدر عندما يكون متاحاً. لا تخترع مصادر غير موجودة.\n\n"
            f"{context}"
        )

    history = [
        {"role": message.role, "content": message.content}
        for message in session.messages
        if message.role in {"user", "assistant"}
    ]
    if not history or history[-1]["content"] != content:
        history.append({"role": "user", "content": content})

    start = time.time()
    answer = await ai_service.get_ai_response(history, system_prompt=system_prompt)
    latency_ms = int((time.time() - start) * 1000)

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        latency_ms=latency_ms,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return assistant_message


async def delete_session(db: Session, session_id: int, user_id: int) -> None:
    """Delete a chat session owned by the current user."""
    session = get_owned_session(db, session_id, user_id)
    db.delete(session)
    db.commit()
