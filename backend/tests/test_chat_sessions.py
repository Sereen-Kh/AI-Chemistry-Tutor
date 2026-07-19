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
from app.models.student_profile import StudentProfile
from app.models.topic import Topic
from app.models.user import User
from app.models.user_progress import UserProgress
from app.services import chat_service
from app.services.learning_memory import build_learning_memory_context
from app.services.rag import RetrievedChunk
from app.services.semantic_rag import SemanticRagResult
from app.services.web_grounding import ExternalSource, WebGroundingResult


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
        unit_id=None,
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
    monkeypatch.setattr(chat_service, "answer_from_book_knowledge", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chat_service, "_dictionary_entry_for_question", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chat_service, "route_direct_answer", lambda *_args, **_kwargs: None)


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
                content="اشرح من الكتاب ما هو التركيز المولي؟",
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


def test_send_message_uses_saved_student_profile_preferences(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            db.add(
                StudentProfile(
                    user_id=user.id,
                    teaching_level="academic",
                    explanation_method="exam_mode",
                    learning_modes=["text", "image"],
                    student_interests=["cars"],
                )
            )
            await db.commit()
            session = await chat_service.create_session(db, user.id, title="تفضيلات")

            assistant = await chat_service.send_message(
                db,
                session_id=session.id,
                user_id=user.id,
                content="اشرح من الكتاب ما هو التركيز المولي؟",
                message_format="auto",
            )

            prefs = assistant.diagnostics["teaching_preferences"]
            assert prefs["teaching_level"] == "academic"
            assert prefs["explanation_method"] == "exam_mode"
            assert prefs["learning_modes"] == ["text", "image"]
            assert prefs["student_interests"] == ["cars"]
            assert assistant.answer_type == "image"

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


def test_session_history_is_bounded_and_preserves_current_question():
    messages = [
        SimpleNamespace(role="user" if index % 2 == 0 else "assistant", content=f"message-{index}")
        for index in range(20)
    ]

    history = chat_service.bounded_session_history(
        messages,
        current_question="current-question",
        max_messages=6,
        max_chars=80,
    )

    assert len(history) <= 6
    assert history[-1] == {"role": "user", "content": "current-question"}
    assert sum(len(item["content"]) for item in history) <= 80
    assert history[0]["content"] != "message-0"


def test_learning_memory_can_be_disabled_from_profile(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            db.add(
                StudentProfile(
                    user_id=user.id,
                    teaching_level="standard",
                    explanation_method="direct",
                    learning_modes=["text"],
                    student_interests=["cars"],
                    metadata_json={"learning_memory_enabled": False},
                )
            )
            await db.commit()
            session = await chat_service.create_session(db, user.id)

            assistant = await chat_service.send_message(
                db,
                session.id,
                user.id,
                "اشرح من الكتاب ما هو التركيز المولي؟",
            )

            assert assistant.diagnostics["learning_memory"] == {
                "enabled": False,
                "applied": False,
                "counts": {},
            }

    run_async(scenario())


def test_learning_memory_uses_only_authenticated_students_records(session_factory):
    async def scenario():
        async with session_factory() as db:
            owner = await _create_user(db, email="memory-owner@example.com")
            other = await _create_user(db, email="memory-other@example.com")
            owner_topic = Topic(title_ar="المحاليل المائية", order=1)
            other_topic = Topic(title_ar="بيانات طالب آخر", order=2)
            db.add_all([owner_topic, other_topic])
            await db.flush()
            db.add_all(
                [
                    UserProgress(
                        user_id=owner.id,
                        topic_id=owner_topic.id,
                        quizzes_completed=2,
                        best_quiz_score=45,
                    ),
                    UserProgress(
                        user_id=other.id,
                        topic_id=other_topic.id,
                        quizzes_completed=3,
                        best_quiz_score=10,
                    ),
                ]
            )
            await db.commit()

            memory = await build_learning_memory_context(db, user_id=owner.id)

            assert "المحاليل المائية" in memory.prompt_text
            assert "بيانات طالب آخر" not in memory.prompt_text
            assert len(memory.prompt_text) <= 1200
            assert memory.diagnostics()["counts"]["weak_topics"] == 1

    run_async(scenario())


def test_new_student_learning_memory_is_safe(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)

            memory = await build_learning_memory_context(db, user_id=user.id)

            assert memory.enabled is True
            assert memory.applied is False
            assert memory.prompt_text == ""
            assert all(value == 0 for value in memory.diagnostics()["counts"].values())

    run_async(scenario())


def test_web_search_is_never_called_without_explicit_request(session_factory, monkeypatch):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("web provider must require explicit user action")

    monkeypatch.setattr(chat_service, "search_web_for_chemistry", fail_if_called)

    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await chat_service.create_session(db, user.id)

            assistant = await chat_service.send_message(db, session.id, user.id, "ما هو الماء؟")

            assert assistant.grounding != "web"

    run_async(scenario())


def test_explicit_web_search_persists_external_sources(session_factory, monkeypatch):
    async def fake_no_results(*_args, **_kwargs):
        return SemanticRagResult(
            chunks=[],
            diagnostics={"pipeline": "test", "cache_hit": False, "quality_gate": {"passed": True}},
        )

    async def fake_web_search(question, **_kwargs):
        assert question == "ما استخدامات الماء في الصناعة؟"
        return WebGroundingResult(
            answer="تُستخدم المياه في التبريد والتنظيف الصناعي.",
            sources=[
                ExternalSource(
                    title="مصدر علمي",
                    url="https://example.org/water",
                    domain="example.org",
                    cited_text="Industrial water is used for cooling.",
                    start_index=0,
                    end_index=20,
                )
            ],
        )

    monkeypatch.setattr(chat_service, "semantic_retrieve_context", fake_no_results)
    monkeypatch.setattr(chat_service, "search_web_for_chemistry", fake_web_search)

    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await chat_service.create_session(db, user.id)
            assistant = await chat_service.send_message(
                db,
                session.id,
                user.id,
                "ما استخدامات الماء في الصناعة؟",
                web_search_requested=True,
            )

            assert assistant.grounding == "web"
            assert assistant.sources == []
            assert assistant.external_sources[0]["domain"] == "example.org"
            reloaded = await chat_service.get_owned_session(db, session.id, user.id)
            assert reloaded.messages[-1].external_sources[0]["url"] == "https://example.org/water"

    run_async(scenario())


def test_web_search_is_not_called_when_book_evidence_is_sufficient(session_factory, monkeypatch):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("web provider must not run when book evidence is sufficient")

    monkeypatch.setattr(chat_service, "search_web_for_chemistry", fail_if_called)

    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await chat_service.create_session(db, user.id)
            assistant = await chat_service.send_message(
                db,
                session.id,
                user.id,
                "اشرح من الكتاب ما هو التركيز المولي؟",
                web_search_requested=True,
            )

            assert assistant.grounding == "book"
            assert assistant.diagnostics["web_search_skipped"] == "BOOK_EVIDENCE_SUFFICIENT"

    run_async(scenario())


def test_web_search_is_rejected_in_book_only_mode(session_factory):
    async def scenario():
        async with session_factory() as db:
            user = await _create_user(db)
            session = await chat_service.create_session(db, user.id)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_message(
                    db,
                    session.id,
                    user.id,
                    "ما هو الماء؟",
                    answer_scope="book_only",
                    web_search_requested=True,
                )
            assert exc_info.value.detail["code"] == "WEB_SEARCH_DISABLED"

    run_async(scenario())
