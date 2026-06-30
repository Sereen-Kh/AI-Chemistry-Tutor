"""Tests for Ask AI audio modality support."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.audio import AudioInputType, RequestedReturnType, ResolvedReturnType, resolve_return_type
from app.services import chat_service
from app.services.audio_service import AudioSynthesisError, AudioTranscriptionError
from app.services.audio_storage import LocalAudioStorage


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


class FakeAudioService:
    def __init__(self, *, transcript: str = "ما هو الماء؟", fail_stt: bool = False, fail_tts: bool = False) -> None:
        self.transcript = transcript
        self.fail_stt = fail_stt
        self.fail_tts = fail_tts
        self.transcribe_calls = 0
        self.synthesize_calls = 0

    async def transcribe_audio(self, *_args, **_kwargs) -> str:
        self.transcribe_calls += 1
        if self.fail_stt:
            raise AudioTranscriptionError("stt failed")
        return self.transcript

    async def synthesize_speech(self, *_args, **_kwargs) -> bytes:
        self.synthesize_calls += 1
        if self.fail_tts:
            raise AudioSynthesisError("tts failed")
        return b"fake-mp3"


async def _create_user_and_session(db: AsyncSession) -> tuple[User, int]:
    user = User(first_name="سارة", email="audio@example.com", hashed_password="hashed")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    session = await chat_service.create_session(db, user.id, title="صوت")
    return user, session.id


@pytest.fixture(autouse=True)
def fake_rag_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_send_message(db: AsyncSession, *, session_id: int, user_id: int, content: str, message_format: str = "text", **_kwargs):
        user_message = ChatMessage(session_id=session_id, role="user", content=content, format="text")
        assistant = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=f"إجابة موثقة: {content}",
            answer_text=f"إجابة موثقة: {content}",
            format=message_format,
            confidence=0.9,
            sources_json=[{"chunk_id": 1, "page_number": 10, "content_type": "definition"}],
        )
        db.add(user_message)
        db.add(assistant)
        await db.commit()
        await db.refresh(assistant)
        return assistant

    monkeypatch.setattr(chat_service, "send_message", fake_send_message)


@pytest.mark.parametrize(
    ("input_type", "requested", "expected"),
    [
        (AudioInputType.TEXT, RequestedReturnType.AUTO, ResolvedReturnType.TEXT),
        (AudioInputType.TEXT, RequestedReturnType.TEXT, ResolvedReturnType.TEXT),
        (AudioInputType.TEXT, RequestedReturnType.AUDIO, ResolvedReturnType.AUDIO),
        (AudioInputType.TEXT, RequestedReturnType.TEXT_AUDIO, ResolvedReturnType.TEXT_AUDIO),
        (AudioInputType.AUDIO, RequestedReturnType.AUTO, ResolvedReturnType.TEXT_AUDIO),
        (AudioInputType.AUDIO, RequestedReturnType.TEXT, ResolvedReturnType.TEXT),
        (AudioInputType.AUDIO, RequestedReturnType.AUDIO, ResolvedReturnType.AUDIO),
        (AudioInputType.AUDIO, RequestedReturnType.TEXT_AUDIO, ResolvedReturnType.TEXT_AUDIO),
    ],
)
def test_return_type_resolver(input_type, requested, expected):
    assert resolve_return_type(input_type, requested) == expected


@pytest.mark.parametrize(
    ("requested", "expected_audio_status", "expects_tts"),
    [
        ("auto", "not_required", False),
        ("text", "not_required", False),
        ("audio", "ready", True),
        ("text_audio", "ready", True),
    ],
)
def test_text_audio_matrix(session_factory, tmp_path: Path, requested: str, expected_audio_status: str, expects_tts: bool):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            audio = FakeAudioService()
            result = await chat_service.send_multimodal_message(
                db,
                session_id=session_id,
                user_id=user.id,
                text="ما هو الماء؟",
                requested_return_type=requested,
                audio_service=audio,
                storage=LocalAudioStorage(tmp_path / "audio"),
            )
            assert result.input_type == "text"
            assert result.answer_text and "إجابة موثقة" in result.answer_text
            assert result.audio_status == expected_audio_status
            assert bool(result.answer_audio_url) is expects_tts
            assert audio.transcribe_calls == 0
            assert audio.synthesize_calls == (1 if expects_tts else 0)

    run_async(scenario())


@pytest.mark.parametrize(
    ("requested", "expected_resolved", "expected_audio_status", "expects_tts"),
    [
        ("auto", "text_audio", "ready", True),
        ("text", "text", "not_required", False),
        ("audio", "audio", "ready", True),
        ("text_audio", "text_audio", "ready", True),
    ],
)
def test_student_audio_matrix(session_factory, tmp_path: Path, requested: str, expected_resolved: str, expected_audio_status: str, expects_tts: bool):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            audio = FakeAudioService(transcript="ما هو التركيز المولي؟")
            result = await chat_service.send_multimodal_message(
                db,
                session_id=session_id,
                user_id=user.id,
                audio_bytes=b"webm-bytes",
                audio_filename="student.webm",
                audio_content_type="audio/webm",
                requested_return_type=requested,
                audio_service=audio,
                storage=LocalAudioStorage(tmp_path / "audio"),
            )
            assert result.input_type == "audio"
            assert result.resolved_return_type == expected_resolved
            assert result.audio_transcript == "ما هو التركيز المولي؟"
            assert result.transcription_status == "ready"
            assert result.audio_status == expected_audio_status
            assert bool(result.answer_audio_url) is expects_tts
            assert audio.transcribe_calls == 1

    run_async(scenario())


def test_missing_text_and_audio_rejected(session_factory, tmp_path: Path):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    audio_service=FakeAudioService(),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "CHAT_INPUT_REQUIRED"

    run_async(scenario())


def test_text_and_audio_together_rejected(session_factory, tmp_path: Path):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    text="سؤال",
                    audio_bytes=b"webm-bytes",
                    audio_filename="student.webm",
                    audio_content_type="audio/webm",
                    audio_service=FakeAudioService(),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "MIXED_INPUT_NOT_SUPPORTED"

    run_async(scenario())


def test_unsupported_audio_format_rejected(session_factory, tmp_path: Path):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    audio_bytes=b"bad",
                    audio_filename="student.txt",
                    audio_content_type="text/plain",
                    audio_service=FakeAudioService(),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "UNSUPPORTED_AUDIO_FORMAT"

    run_async(scenario())


def test_audio_too_large_rejected(session_factory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat_service.settings, "audio_max_file_size_mb", 0)

    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    audio_bytes=b"webm-bytes",
                    audio_filename="student.webm",
                    audio_content_type="audio/webm",
                    audio_service=FakeAudioService(),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "AUDIO_FILE_TOO_LARGE"

    run_async(scenario())


def test_stt_failure_blocks_rag(session_factory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    called = False

    async def fail_if_called(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(chat_service, "send_message", fail_if_called)

    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    audio_bytes=b"webm-bytes",
                    audio_filename="student.webm",
                    audio_content_type="audio/webm",
                    audio_service=FakeAudioService(fail_stt=True),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "TRANSCRIPTION_FAILED"
            assert called is False

    run_async(scenario())


def test_tts_failure_keeps_text_answer(session_factory, tmp_path: Path):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            result = await chat_service.send_multimodal_message(
                db,
                session_id=session_id,
                user_id=user.id,
                text="ما هو الماء؟",
                requested_return_type="audio",
                audio_service=FakeAudioService(fail_tts=True),
                storage=LocalAudioStorage(tmp_path / "audio"),
            )
            assert result.answer_text
            assert result.answer_audio_url is None
            assert result.audio_status == "failed"

    run_async(scenario())


def test_missing_provider_key_returns_clear_error(session_factory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat_service.settings, "audio_enabled", True)
    monkeypatch.setattr(chat_service.settings, "elevenlabs_api_key", "")
    monkeypatch.setattr(chat_service.settings, "elevenlabs_default_voice_id", "voice")

    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    text="ما هو الماء؟",
                    requested_return_type="audio",
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "AUDIO_PROVIDER_NOT_CONFIGURED"

    run_async(scenario())
