from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.assessment import QuizAttempt
from app.models.chemistry import Chapter, Lesson, Unit
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk
from app.models.topic import Topic
from app.models.user import User
from app.services.quiz_service import QUIZ_NOT_READY_CODE, generate_quiz, submit_quiz


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


async def _seed_quiz_context(
    db: AsyncSession,
    *,
    quality_status: str = "ready",
) -> tuple[Lesson, Topic, ExtractedQuestion]:
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
    user = User(first_name="Quiz", last_name="User", email="quiz@example.com", hashed_password="x")
    source = ContentSource(source_type="textbook", title="Chemistry", status="completed")
    db.add_all([lesson, user, source])
    await db.flush()
    chunk = RagChunk(
        source_id=source.id,
        unit_id=unit.id,
        chapter_id=chapter.id,
        lesson_id=lesson.id,
        topic_id=topic.id,
        page_number=110,
        chunk_index=0,
        content="قانون التركيز المولي C = n / V",
        normalized_content="قانون التركيز المولي C = n / V",
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
    question = ExtractedQuestion(
        source_id=source.id,
        lesson_id=lesson.id,
        topic_id=topic.id,
        page_number=110,
        question_text="ما قانون التركيز المولي؟",
        question_type="multiple_choice",
        options=["C = n / V", "m = C / V", "V = C × n", "n = C + V"],
        correct_answer="C = n / V",
        explanation="التركيز المولي يساوي كمية المادة مقسومة على الحجم.",
        difficulty=3,
        needs_review=False,
    )
    db.add_all([chunk, question])
    await db.commit()
    await db.refresh(lesson)
    await db.refresh(topic)
    await db.refresh(question)
    return lesson, topic, question


def test_quiz_generation_allows_ready_reviewed_lesson(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with session_factory() as db:
            lesson, _topic, _question = await _seed_quiz_context(db, quality_status="ready")
            questions, generated, source = await generate_quiz(
                db,
                lesson_ids=[lesson.id],
                limit=1,
                question_types=["mcq"],
            )

            assert generated is False
            assert source == "database"
            assert len(questions) == 1
            assert questions[0].lesson_id == lesson.id

    run_async(scenario())


def test_quiz_generation_blocks_needs_review_lesson(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with session_factory() as db:
            lesson, _topic, _question = await _seed_quiz_context(db, quality_status="needs_review")
            with pytest.raises(HTTPException) as exc:
                await generate_quiz(db, lesson_ids=[lesson.id], limit=1)

            assert exc.value.status_code == 409
            assert isinstance(exc.value.detail, dict)
            assert exc.value.detail["code"] == QUIZ_NOT_READY_CODE
            assert exc.value.detail["quality_status"] == "needs_review"

    run_async(scenario())


def test_quiz_submission_persists_real_answers_without_hardcoded_topic(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with session_factory() as db:
            _lesson, topic, question = await _seed_quiz_context(db, quality_status="ready")
            attempt = await submit_quiz(db, user_id=1, topic_id=None, answers={str(question.id): "C = n / V"})

            assert attempt.topic_id == topic.id
            assert attempt.score == 1
            assert attempt.total == 1
            stored = await db.scalar(select(QuizAttempt).where(QuizAttempt.id == attempt.id))
            assert stored is not None
            assert stored.answers == {str(question.id): "C = n / V"}

    run_async(scenario())
