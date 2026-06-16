"""Flashcard service functions."""

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcard import Flashcard, FlashcardProgress
from app.models.textbook import RagChunk
from app.models.topic import Topic
from app.schemas.flashcards import FlashcardGenerateRequest


async def list_flashcards(db: AsyncSession, topic_id: int | None = None) -> list[Flashcard]:
    stmt = select(Flashcard)
    if topic_id is not None:
        stmt = stmt.where(Flashcard.topic_id == topic_id)
    result = await db.execute(stmt.order_by(Flashcard.id))
    return list(result.scalars().all())


async def create_flashcard(db: AsyncSession, data: dict) -> Flashcard:
    card = Flashcard(**data)
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


def _front_from_content(content: str) -> str:
    first = content.strip().splitlines()[0] if content.strip() else "مفهوم كيميائي"
    return first[:140]


def _back_from_content(content: str) -> str:
    cleaned = " ".join(content.split())
    return cleaned[:500] or "راجع مصدر الدرس للإجابة."


async def generate_flashcards(
    db: AsyncSession,
    request: FlashcardGenerateRequest,
) -> list[Flashcard]:
    topic_id = request.topic_id
    if topic_id is None:
        topic = await db.scalar(select(Topic).order_by(Topic.order, Topic.id).limit(1))
        if topic is None:
            raise HTTPException(status_code=404, detail="No topic is available for flashcard generation")
        topic_id = topic.id

    cards: list[Flashcard] = []
    if request.source_text and request.source_text.strip():
        snippets = [part.strip() for part in request.source_text.split("\n") if part.strip()][: request.limit]
        for snippet in snippets:
            cards.append(
                Flashcard(
                    topic_id=topic_id,
                    front_ar=_front_from_content(snippet),
                    back_ar=_back_from_content(snippet),
                    created_by=request.created_by,
                )
            )
    else:
        source_filter = RagChunk.topic_id == topic_id
        if request.lesson_id is not None:
            source_filter = or_(source_filter, RagChunk.lesson_id == request.lesson_id)
        stmt = (
            select(RagChunk)
            .where(
                source_filter,
                RagChunk.content_type.in_(("definition", "formula", "equation", "result", "note", "text")),
            )
            .order_by(RagChunk.page_number.asc(), RagChunk.chunk_index.asc())
            .limit(request.limit)
        )
        result = await db.execute(stmt)
        for chunk in result.scalars().all():
            cards.append(
                Flashcard(
                    topic_id=topic_id,
                    front_ar=_front_from_content(chunk.content),
                    back_ar=_back_from_content(chunk.content),
                    created_by=request.created_by,
                )
            )

    if not cards:
        topic = await db.get(Topic, topic_id)
        cards.append(
            Flashcard(
                topic_id=topic_id,
                front_ar=topic.title_ar if topic else "مراجعة كيمياء",
                back_ar=topic.description_ar if topic and topic.description_ar else "اكتب تعريفاً مختصراً لهذا المفهوم ثم راجع المصدر.",
                created_by=request.created_by,
            )
        )

    db.add_all(cards)
    await db.commit()
    for card in cards:
        await db.refresh(card)
    return cards[: request.limit]


async def due_flashcards(db: AsyncSession, user_id: int, limit: int = 30) -> list[tuple[Flashcard, FlashcardProgress | None]]:
    today = date.today()
    result = await db.execute(
        select(Flashcard, FlashcardProgress)
        .outerjoin(
            FlashcardProgress,
            (FlashcardProgress.flashcard_id == Flashcard.id) & (FlashcardProgress.user_id == user_id),
        )
        .where(
            or_(
                FlashcardProgress.id.is_(None),
                FlashcardProgress.mastered.is_(False),
                FlashcardProgress.next_review_at.is_(None),
                FlashcardProgress.next_review_at <= today,
            )
        )
        .order_by(Flashcard.id.asc())
        .limit(limit)
    )
    return list(result.all())


async def review_flashcard(db: AsyncSession, user_id: int, flashcard_id: int, quality: int) -> FlashcardProgress:
    card = await db.get(Flashcard, flashcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    result = await db.execute(
        select(FlashcardProgress).where(
            FlashcardProgress.user_id == user_id,
            FlashcardProgress.flashcard_id == flashcard_id,
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = FlashcardProgress(user_id=user_id, flashcard_id=flashcard_id)
        db.add(progress)
    progress.review_count += 1
    progress.mastered = quality >= 4
    progress.interval_days = max(1, quality * 2)
    progress.next_review_at = date.today() + timedelta(days=progress.interval_days)
    progress.last_reviewed = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(progress)
    return progress
