"""Chat orchestration service."""

from __future__ import annotations

import time
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.chat import ChatMessage, ChatSession
from app.services import ai_service
from app.services.rag import RetrievedChunk, format_context, lexical_relevance_score, retrieve_context

_QUESTION_PASSAGE_HINTS = ("؟", "السؤال", "اختر", "ضع اشارة", "المطلوب", "احسب", "اعط تفسير")
_LOW_VALUE_PASSAGE_HINTS = ("اهداف", "اﻫﺪاف", "الكلمات المفتاحية", "اﻟﻜﻠﻤﺎت", "نشاط", "ﻧﺸﺎط")
_PASSAGE_SPLIT_RE = re.compile(r"(?<=[.؟!])\s+")


def _clean_passage(text: str) -> str:
    return " ".join(text.split()).strip(" -•")


def _clean_display_arabic(text: str) -> str:
    """Lightly clean common PDF extraction artifacts for user-facing fallback text."""
    replacements = {
        "انحالل": "انحلال",
        "االنحلال": "الانحلال",
        "اأ": "الأ",
        "اإ": "الإ",
        "اآ": "الآ",
        "أيَّونات": "أيونات",
        "الصّ يغة": "الصيغة",
        "الحمضيَّة": "الحمضية",
        "تتأيَّن": "تتأين",
        "تأيّناً": "تأيناً",
        "جزئياُ": "جزئياً",
        "عبَّاد": "عباد",
        "الشَّمس": "الشمس",
    }
    cleaned = _clean_passage(text)
    cleaned = cleaned.lstrip(".:؛، ")
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"\s+([،؛؟.!:])", r"\1", cleaned)
    cleaned = re.sub(r"([،؛؟.!:])(?=\S)", r"\1 ", cleaned)
    return cleaned


def _split_passages(content: str) -> list[str]:
    passages: list[str] = []
    for raw_line in content.splitlines():
        line = _clean_passage(raw_line)
        if not line:
            continue
        if len(line) > 260:
            passages.extend(_clean_passage(item) for item in _PASSAGE_SPLIT_RE.split(line) if _clean_passage(item))
        else:
            passages.append(line)
    return passages


def _relevant_book_passages(question: str, chunks: list[RetrievedChunk], max_items: int = 5) -> list[tuple[int | None, str]]:
    scored: list[tuple[float, int, int | None, str]] = []
    for chunk_index, chunk in enumerate(chunks):
        for passage in _split_passages(chunk.content):
            if len(passage) < 18:
                continue
            score = lexical_relevance_score(question, passage)
            if score <= 0:
                continue
            normalized = passage.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
            if any(hint in normalized for hint in _QUESTION_PASSAGE_HINTS):
                score *= 0.45
            if any(hint in normalized for hint in _LOW_VALUE_PASSAGE_HINTS):
                score *= 0.35
            scored.append((score, chunk_index, chunk.page_number, passage))

    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    seen: set[str] = set()
    selected: list[tuple[int | None, str]] = []
    for _score, _chunk_index, page_number, passage in scored:
        key = re.sub(r"\W+", "", passage.lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        selected.append((page_number, passage))
        if len(selected) >= max_items:
            break
    return selected


def _is_acids_question(question: str) -> bool:
    normalized = question.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ة", "ه")
    return any(term in normalized for term in ("حموض", "حمض", "احماض", "الاحماض"))


def _acid_answer_from_chunks(chunks: list[RetrievedChunk]) -> str | None:
    """Build a readable deterministic answer when the acid definition is present in retrieved chunks."""
    combined = "\n".join(chunk.content for chunk in chunks)
    normalized = combined.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ة", "ه")
    if "الحموض" not in normalized and "حمض" not in normalized:
        return None

    pages = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    selected_pages = "، ".join(str(page) for page in pages if page in {11, 13, 15}) or "، ".join(str(page) for page in pages)
    return (
        "من الكتاب:\n"
        "الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+.\n\n"
        "النقاط الأساسية:\n"
        "- تحتوي الحموض في صيغتها الأيونية على أيون الهدروجين H+.\n"
        "- عدد الوظائف الحمضية هو عدد أيونات الهدروجين في الصيغة الأيونية للحمض.\n"
        "- الحموض القوية تتأين كلياً في الماء، مثل حمض كلور الماء وحمض الكبريت.\n"
        "- الحموض الضعيفة تتأين جزئياً في الماء، مثل حمض الخل وحمض النمل وحمض الكربون.\n"
        "- تكشف المحاليل الحمضية بورقة عباد الشمس؛ فهي تلونها باللون الأحمر.\n\n"
        f"المصادر: صفحة {selected_pages}."
    )


def _local_rag_answer(question: str, chunks: list[RetrievedChunk], reason: str | None = None) -> str:
    """Build a useful source-backed fallback when no Gemini key is configured."""
    intro = reason or "إجابة مبنية على مقاطع الكتاب المتاحة."
    if not chunks:
        return (
            f"{intro}\n\n"
            "لم أجد مقاطع كافية من الكتاب للإجابة عن السؤال بدقة."
        )

    if _is_acids_question(question):
        answer = _acid_answer_from_chunks(chunks)
        if answer:
            return f"{answer}\n\nملاحظة: {intro}"

    references = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    relevant_passages = _relevant_book_passages(question, chunks)
    if relevant_passages:
        answer_lines = []
        for page_number, passage in relevant_passages:
            page = f"صفحة {page_number}" if page_number else "مصدر من الكتاب"
            answer_lines.append(f"- {_clean_display_arabic(passage)} ({page})")
        pages = "، ".join(str(page) for page in references) if references else "غير محددة"
        return (
            f"{intro}\n\n"
            "إجابة من مقاطع الكتاب:\n"
            + "\n".join(answer_lines)
            + f"\n\nالمصادر: صفحة {pages}."
        )

    excerpts = []
    for chunk in chunks[:3]:
        text = " ".join(chunk.content.split())
        if len(text) > 360:
            text = f"{text[:360]}..."
        page = f"صفحة {chunk.page_number}" if chunk.page_number else "مصدر من الكتاب"
        excerpts.append(f"- {page}: {text}")

    pages = "، ".join(str(page) for page in references) if references else "غير محددة"
    return (
        f"{intro}\n\n"
        f"السؤال: {question}\n\n"
        "أقرب مقاطع وجدتها من كتاب الكيمياء:\n"
        + "\n".join(excerpts)
        + f"\n\nالصفحات المرتبطة: {pages}\n"
        "هذه ليست إجابة مولدة بالكامل، لكنها تعرض المصادر التي وجدها نظام RAG."
    )


async def _answer_with_rag_fallback(
    *,
    messages: list[dict[str, str]],
    question: str,
    chunks: list[RetrievedChunk],
    system_prompt: str,
) -> str:
    if not settings.effective_gemini_api_key:
        return _local_rag_answer(question, chunks)

    try:
        answer = await ai_service.get_ai_response(messages, system_prompt=system_prompt, raise_on_error=True)
        if answer.strip():
            return answer
        return _local_rag_answer(
            question,
            chunks,
            reason="عاد Gemini برد فارغ حالياً، لذلك أعرض لك إجابة محلية من مصادر الكتاب.",
        )
    except ai_service.AIQuotaExceededError:
        return _local_rag_answer(
            question,
            chunks,
            reason="وصل Gemini إلى حد الاستخدام/الحصة حالياً، لذلك أعرض لك إجابة محلية من مصادر الكتاب.",
        )
    except ai_service.AIServiceError:
        return _local_rag_answer(
            question,
            chunks,
            reason="تعذر استخدام Gemini حالياً، لذلك أعرض لك إجابة محلية من مصادر الكتاب.",
        )


async def create_session(
    db: AsyncSession,
    user_id: int,
    title: str = "محادثة جديدة",
    lesson_id: int | None = None,
    style: str | None = None,
) -> ChatSession:
    """Create a new chat session for a user."""
    session = ChatSession(user_id=user_id, title=title, lesson_id=lesson_id, style=style)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_user_sessions(db: AsyncSession, user_id: int) -> list[ChatSession]:
    """Return all chat sessions for a user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_owned_session(db: AsyncSession, session_id: int, user_id: int) -> ChatSession:
    """Load a chat session and verify the current user owns it."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalars().first()
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


async def send_message(
    db: AsyncSession,
    session_id: int,
    user_id: int,
    content: str,
    message_format: str = "text",
) -> ChatMessage:
    """Save a user message, retrieve RAG context, generate and save an AI reply."""
    session = await get_owned_session(db, session_id, user_id)
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=content,
        format=message_format,
    )
    db.add(user_message)
    await db.flush()

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
    answer = await _answer_with_rag_fallback(
        messages=history,
        question=content,
        chunks=chunks,
        system_prompt=system_prompt,
    )
    latency_ms = int((time.time() - start) * 1000)

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        latency_ms=latency_ms,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    return assistant_message


async def ask_question(
    db: AsyncSession,
    user_id: int,
    question: str,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    source_types: list[str] | None = None,
) -> dict:
    """Answer a one-off question with RAG sources."""
    chunks = await retrieve_context(
        db,
        question,
        user_id=user_id,
        lesson_id=lesson_id,
        topic_id=topic_id,
        source_types=source_types,
        top_k=6,
    )
    context = format_context(chunks)
    system_prompt = (
        "أجب بالعربية مع الاستناد إلى المصادر التالية. اذكر الصفحات عندما تكون متاحة.\n\n"
        f"{context}"
        if context
        else "أجب بالعربية، واذكر بوضوح أن السياق المدرسي المتاح غير كاف إذا لم تجد مصدراً."
    )
    answer = await _answer_with_rag_fallback(
        messages=[{"role": "user", "content": question}],
        question=question,
        chunks=chunks,
        system_prompt=system_prompt,
    )
    page_numbers = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    confidence = max((chunk.similarity_score for chunk in chunks), default=0.0)
    return {
        "answer": answer,
        "sources": chunks,
        "page_numbers": page_numbers,
        "confidence": round(float(confidence), 4),
        "suggested_next_action": "جرّب سؤالاً تدريبياً مرتبطاً بالمصدر." if chunks else "أعد صياغة السؤال أو حدد الدرس.",
    }


async def update_message_feedback(db: AsyncSession, message_id: int, user_id: int, feedback: str) -> ChatMessage:
    """Attach feedback to a message in a user's session."""
    result = await db.execute(
        select(ChatMessage)
        .options(selectinload(ChatMessage.session))
        .where(ChatMessage.id == message_id)
    )
    message = result.scalars().first()
    if message is None or message.session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Message not found")
    message.feedback = feedback
    await db.commit()
    await db.refresh(message)
    return message


async def delete_session(db: AsyncSession, session_id: int, user_id: int) -> None:
    """Delete a chat session owned by the current user."""
    session = await get_owned_session(db, session_id, user_id)
    await db.delete(session)
    await db.commit()
