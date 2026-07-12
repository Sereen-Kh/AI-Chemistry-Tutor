from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.chemistry import Chapter, Lesson, Unit
from app.models.textbook import ContentSource, RagChunk
from app.models.topic import Topic
from app.models.user import User
from app.schemas.flashcards import FlashcardGenerateRequest
from app.services.flashcard_service import (
    FLASHCARD_ADMIN_APPROVAL_CODE,
    FLASHCARD_BLOCKED_CODE,
    generate_flashcard_deck,
    get_deck,
)


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture()
def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def init() -> async_sessionmaker[AsyncSession]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    factory = run_async(init())
    yield factory
    run_async(engine.dispose())


async def _seed_flashcard_context(
    db: AsyncSession,
    *,
    quality_status: str = "ready",
) -> tuple[User, Lesson]:
    unit = Unit(unit_number=4, semester=2, title_ar="الكيمياء اللاعضوية", order=4)
    chapter = Chapter(unit=unit, title_ar="المحاليل", order=1)
    topic = Topic(title_ar="التركيز المولي", order=1, difficulty=2)
    lesson = Lesson(
        chapter=chapter,
        title_ar="المحاليل المائية",
        content_ar="درس عن المحاليل المائية والتركيز.",
        order=1,
        difficulty=2,
        duration_min=30,
        page_start=108,
        page_end=115,
        topics=[topic],
    )
    user = User(first_name="Flash", last_name="User", email="flash@example.com", hashed_password="x")
    source = ContentSource(source_type="textbook", title="Chemistry", status="completed")
    db.add_all([lesson, user, source])
    await db.flush()
    db.add(
        RagChunk(
            source_id=source.id,
            unit_id=unit.id,
            chapter_id=chapter.id,
            lesson_id=lesson.id,
            topic_id=topic.id,
            page_number=110,
            chunk_index=0,
            content=(
                "التركيز المولي هو كمية المادة بالمول في حجم معين من المحلول، "
                "ويحسب من العلاقة C = n / V مع الانتباه لوحدة الحجم بالليتر."
            ),
            normalized_content="التركيز المولي هو كمية المادة بالمول في حجم معين من المحلول",
            content_type="formula",
            source_type="textbook",
            metadata_json={
                "unit_id": "unit_04",
                "lesson_id": "unit_04_lesson_01",
                "source_type": "textbook",
                "printed_page_start": 110,
                "printed_page_end": 110,
                "quality_status": quality_status,
                "reviewed_metadata_version": "2026-06-reviewed-v1",
            },
        )
    )
    await db.commit()
    await db.refresh(user)
    await db.refresh(lesson)
    return user, lesson


def _request(lesson_id: int, **overrides) -> FlashcardGenerateRequest:
    return FlashcardGenerateRequest(
        lesson_ids=[lesson_id],
        cards_per_lesson=2,
        card_types=["term_definition", "concept_explanation"],
        difficulty="mixed",
        **overrides,
    )


def test_flashcard_generation_allows_ready_reviewed_lesson(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with session_factory() as db:
            user, lesson = await _seed_flashcard_context(db, quality_status="ready")
            deck = await generate_flashcard_deck(db, user.id, _request(lesson.id))
            _deck, rows, stats = await get_deck(db, user.id, deck.id)

            assert stats["total_cards"] == 2
            for card, _progress in rows:
                assert card.front_ar
                assert card.back_ar
                assert card.hint_ar
                assert card.explanation_ar
                assert card.source_page_start == 110
                assert card.metadata_json["quality_status"] == "ready"
                assert card.metadata_json["reviewed_metadata_version"] == "2026-06-reviewed-v1"

    run_async(scenario())


def test_flashcard_generation_blocks_needs_review_for_student(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with session_factory() as db:
            user, lesson = await _seed_flashcard_context(db, quality_status="needs_review")
            with pytest.raises(HTTPException) as exc:
                await generate_flashcard_deck(db, user.id, _request(lesson.id))

            assert exc.value.status_code == 403
            assert isinstance(exc.value.detail, dict)
            assert exc.value.detail["code"] == FLASHCARD_ADMIN_APPROVAL_CODE
            assert exc.value.detail["quality_status"] == "needs_review"

    run_async(scenario())


def test_flashcard_generation_allows_needs_review_with_explicit_admin_approval(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with session_factory() as db:
            user, lesson = await _seed_flashcard_context(db, quality_status="needs_review")
            deck = await generate_flashcard_deck(
                db,
                user.id,
                _request(lesson.id, allow_needs_review=True, admin_review_approved=True),
            )
            _deck, rows, stats = await get_deck(db, user.id, deck.id)

            assert stats["total_cards"] == 2
            assert {card.metadata_json["quality_status"] for card, _progress in rows} == {"needs_review"}

    run_async(scenario())


def test_flashcard_generation_blocks_blocked_lesson(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with session_factory() as db:
            user, lesson = await _seed_flashcard_context(db, quality_status="blocked")
            with pytest.raises(HTTPException) as exc:
                await generate_flashcard_deck(db, user.id, _request(lesson.id))

            assert exc.value.status_code == 409
            assert isinstance(exc.value.detail, dict)
            assert exc.value.detail["code"] == FLASHCARD_BLOCKED_CODE
            assert exc.value.detail["quality_status"] == "blocked"

    run_async(scenario())
