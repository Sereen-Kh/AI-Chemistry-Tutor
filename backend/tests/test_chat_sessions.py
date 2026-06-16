"""Tests for persistent chat sessions and rich assistant metadata."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.chat import ChatMessage
from app.models.user import User
from app.services import chat_service
from app.services.rag import RetrievedChunk
from app.services.semantic_rag import SemanticRagResult


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


@pytest.fixture(autouse=True)
def deterministic_chat_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = RetrievedChunk(
        id=42,
        source_id=7,
        content="التركيز المولي يحسب بالعلاقة C = n / V.",
        source="syria_grade_9_chemistry",
        source_type="textbook",
        content_type="definition",
        page_number=11,
        chapter_id=None,
        lesson_id=None,
        topic_id=None,
        metadata_json={},
        similarity_score=0.86,
    )

    async def fake_semantic_retrieve_context(*_args, **_kwargs):
        return SemanticRagResult(
            chunks=[chunk],
            diagnostics={
                "pipeline": "test",
                "cache_hit": False,
                "quality_gate": {"passed": True},
            },
        )

    async def fake_route_source(*_args, **_kwargs):
        return SimpleNamespace(
            route="balanced",
            source_types=["textbook"],
            reason="test",
            confidence=1.0,
            matched_terms=[],
            cache_hit=False,
        )

    async def fake_answer(*_args, messages, **_kwargs):
        assert any(message["role"] == "user" for message in messages)
        return "الإجابة الموثقة: C = n / V من صفحة 11."

    monkeypatch.setattr(chat_service, "semantic_retrieve_context", fake_semantic_retrieve_context)
    monkeypatch.setattr(chat_service, "route_source", fake_route_source)
    monkeypatch.setattr(chat_service, "_answer_with_rag_fallback", fake_answer)


async def _create_user(db: AsyncSession, *, email: str = "student@example.com") -> User:
    user = User(first_name="سارة", last_name="", email=email, hashed_password="hashed")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def test_create_and_list_sessions(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            first = await chat_service.create_session(db, user.id, title="الأولى")
            second = await chat_service.create_session(db, user.id, title="الثانية")

            sessions = await chat_service.get_user_sessions(db, user.id)

            assert {session.id for session in sessions} == {first.id, second.id}
            assert all(isinstance(session.messages, list) for session in sessions)

    run_async(scenario())


def test_user_cannot_access_another_users_session(session_factory):
    async def scenario():
        async with session_factory() as db:
            owner = await _create_user(db, email="owner@example.com")
            other = await _create_user(db, email="other@example.com")
            session = await chat_service.create_session(db, owner.id)

            with pytest.raises(HTTPException) as exc_info:
                await chat_service.get_owned_session(db, session.id, other.id)

            assert exc_info.value.status_code == 404

    run_async(scenario())


def test_send_message_persists_user_and_rich_assistant_message(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await chat_service.create_session(db, user.id, title="تركيز")

            assistant = await chat_service.send_message(
                db,
                session_id=session.id,
                user_id=user.id,
                content="ما هو التركيز المولي؟",
                message_format="image",
                learning_modes=["text", "image"],
                teaching_level="simple",
                explanation_method="step_by_step",
            )

            assert assistant.role == "assistant"
            assert "C = n / V" in assistant.content
            assert assistant.confidence is not None and assistant.confidence > 0
            assert assistant.answer_type == "image"
            assert assistant.sources[0]["chunk_id"] == 42
            assert assistant.page_numbers == [11]
            assert assistant.source_blocks[0]["page"] == 11
            assert assistant.diagnostics["teaching_preferences"]["teaching_level"] == "simple"

            count = await db.scalar(
                select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session.id)
            )
            assert count == 2

    run_async(scenario())


def test_session_updated_at_changes_after_message(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await chat_service.create_session(db, user.id)
            before = session.updated_at

            await chat_service.send_message(db, session.id, user.id, "ما هو التركيز المولي؟")
            refreshed = await chat_service.get_owned_session(db, session.id, user.id)

            assert refreshed.updated_at >= before

    run_async(scenario())


def test_delete_session_cascades_messages(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await chat_service.create_session(db, user.id)
            await chat_service.send_message(db, session.id, user.id, "ما هو التركيز المولي؟")

            await chat_service.delete_session(db, session.id, user.id)

            with pytest.raises(HTTPException):
                await chat_service.get_owned_session(db, session.id, user.id)
            count = await db.scalar(select(func.count(ChatMessage.id)))
            assert count == 0

    run_async(scenario())
