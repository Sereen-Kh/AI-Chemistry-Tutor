"""Tests for Ask AI audio modality support."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_current_user_id
from app.database import Base
from app.database import get_async_db
from app.main import app
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.audio import AudioInputType, RequestedReturnType, ResolvedReturnType, resolve_return_type
from app.services import chat_service
from app.services.audio_service import AudioService, AudioSynthesisError, AudioTranscriptionError, TTSProvider
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
        self.synthesized_texts: list[str] = []

    async def transcribe_audio(self, *_args, **_kwargs) -> str:
        self.transcribe_calls += 1
        if self.fail_stt:
            raise AudioTranscriptionError("stt failed")
        return self.transcript

    async def synthesize_speech(self, text: str, *_args, **_kwargs) -> bytes:
        self.synthesize_calls += 1
        self.synthesized_texts.append(text)
        if self.fail_tts:
            raise AudioSynthesisError("tts failed")
        return b"fake-mp3"


class FakeTTSProvider(TTSProvider):
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str, str]] = []

    async def synthesize(self, text: str, *, voice_id: str, language: str = "auto") -> bytes:
        self.calls.append((text, voice_id, language))
        if self.fail:
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
            sources_json=[
                {
                    "chunk_id": 1,
                    "source_id": 2,
                    "source_type": "textbook",
                    "page_number": 108,
                    "printed_page_start": 108,
                    "printed_page_end": 108,
                    "unit_id": "unit_04",
                    "lesson_id": "unit_04_lesson_01",
                    "content_type": "definition",
                    "similarity_score": 0.9,
                    "quality_status": "ready",
                    "reviewed_metadata_version": "2026-06-reviewed-v1",
                    "curriculum_metadata": {
                        "source_type": "textbook",
                        "unit_id": "unit_04",
                        "lesson_id": "unit_04_lesson_01",
                        "printed_page_start": 108,
                        "printed_page_end": 108,
                        "quality_status": "ready",
                        "reviewed_metadata_version": "2026-06-reviewed-v1",
                        "stale": False,
                    },
                }
            ],
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


def test_tts_service_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat_service.settings, "tts_max_chars_per_response", 1200)
    monkeypatch.setattr(chat_service.settings, "elevenlabs_default_voice_id", "voice-1")
    provider = FakeTTSProvider()
    service = AudioService(tts_provider=provider)

    result = run_async(service.synthesize_speech("إجابة كيميائية", language="ar"))

    assert result == b"fake-mp3"
    assert provider.calls == [("إجابة كيميائية", "voice-1", "ar")]


def test_tts_service_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat_service.settings, "tts_max_chars_per_response", 1200)
    monkeypatch.setattr(chat_service.settings, "elevenlabs_default_voice_id", "voice-1")
    service = AudioService(tts_provider=FakeTTSProvider(fail=True))

    with pytest.raises(AudioSynthesisError):
        run_async(service.synthesize_speech("إجابة كيميائية", language="ar"))


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
            if expects_tts:
                assert audio.synthesized_texts == [result.answer_text]

            stored_messages = list(
                (await db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id))).all()
            )
            assert [message.role for message in stored_messages] == ["user", "assistant"]
            assert stored_messages[0].content == "ما هو التركيز المولي؟"
            assert stored_messages[0].audio_transcript == "ما هو التركيز المولي؟"
            assert stored_messages[1].answer_text
            assert stored_messages[1].sources_json[0]["unit_id"] == "unit_04"
            assert stored_messages[1].sources_json[0]["lesson_id"] == "unit_04_lesson_01"

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


def test_empty_audio_rejected(session_factory, tmp_path: Path):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    audio_bytes=b"",
                    audio_filename="student.webm",
                    audio_content_type="audio/webm",
                    audio_service=FakeAudioService(),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "AUDIO_EMPTY"

    run_async(scenario())


def test_unified_chat_rejects_expired_authentication():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/messages",
            data={
                "conversationId": "1",
                "text": "ما هو الماء؟",
                "requestedReturnType": "text",
            },
            headers={"Authorization": "Bearer expired.invalid.token"},
        )

    assert response.status_code in {401, 403}


def test_missing_audio_mime_type_rejected(session_factory, tmp_path: Path):
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
                    audio_content_type=None,
                    audio_service=FakeAudioService(),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "UNSUPPORTED_AUDIO_FORMAT"

    run_async(scenario())


def test_invalid_requested_return_type_rejected(session_factory, tmp_path: Path):
    async def scenario():
        async with session_factory() as db:
            user, session_id = await _create_user_and_session(db)
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.send_multimodal_message(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    text="ما هو الماء؟",
                    requested_return_type="voice",
                    audio_service=FakeAudioService(),
                    storage=LocalAudioStorage(tmp_path / "audio"),
                )
            assert exc_info.value.detail["code"] == "INVALID_REQUESTED_RETURN_TYPE"

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


def test_audio_storage_uses_opaque_media_urls(tmp_path: Path):
    storage = LocalAudioStorage(tmp_path / "audio")
    input_path, input_url = storage.save_input_bytes(
        b"webm-bytes",
        filename="student private name.webm",
        content_type="audio/webm",
    )
    output_path, output_url = storage.save_output_bytes(b"mp3-bytes", message_id=123)

    assert input_path.exists()
    assert output_path.exists()
    assert input_path.name.startswith("input_")
    assert "student" not in input_path.name
    assert "private" not in input_path.name
    assert output_path.name.startswith("answer_123_")
    assert output_path.name != "answer_123.mp3"
    assert input_url.startswith("/media/uploads/")
    assert output_url.startswith("/media/uploads/")
    assert not input_url.startswith("file://")
    assert not output_url.startswith("file://")


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


def test_ask_answer_tts_missing_provider_returns_failed_status(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat_service.settings, "audio_enabled", True)
    monkeypatch.setattr(chat_service.settings, "elevenlabs_api_key", "")
    monkeypatch.setattr(chat_service.settings, "elevenlabs_default_voice_id", "voice")

    result = run_async(chat_service.synthesize_ask_answer_audio("إجابة نصية جاهزة"))

    assert result["audio_url"] is None
    assert result["audio_status"] == "failed"
    assert result["audio_error"]["code"] == "AUDIO_PROVIDER_NOT_CONFIGURED"


@pytest.fixture()
def ask_ai_client():
    async def fake_db():
        yield object()

    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_async_db] = fake_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
        app.dependency_overrides.pop(get_async_db, None)


def _fake_ask_result() -> dict:
    return {
        "answer": "الماء مركب كيميائي يتكون من الهيدروجين والأكسجين.",
        "answer_text": "الماء مركب كيميائي يتكون من الهيدروجين والأكسجين.",
        "answer_type": "audio",
        "route": "textbook_rag",
        "grounding": "book",
        "answer_scope": "auto",
        "teaching_level": "standard",
        "explanation_method": "direct",
        "learning_modes": ["audio"],
        "student_interests": [],
        "blocks": [{"type": "text", "content": "الماء مركب كيميائي يتكون من الهيدروجين والأكسجين."}],
        "sources": [
            SimpleNamespace(
                id=1,
                source_id=2,
                source="syria_grade_9_chemistry",
                source_type="textbook",
                page_number=108,
                content_type="definition",
                unit_id="unit_04",
                lesson_id="unit_04_lesson_01",
                quality_status="ready",
                quality_warning=None,
                reviewed_metadata_version="2026-06-reviewed-v1",
                curriculum_metadata={
                    "source_type": "textbook",
                    "unit_id": "unit_04",
                    "lesson_id": "unit_04_lesson_01",
                    "printed_page_start": 108,
                    "printed_page_end": 108,
                    "quality_status": "ready",
                    "reviewed_metadata_version": "2026-06-reviewed-v1",
                    "stale": False,
                },
                similarity_score=0.91,
            )
        ],
        "citations": [],
        "media_blocks": [],
        "source_blocks": [{"chunk_id": 1, "chunk_type": "definition", "score": 0.91}],
        "page_numbers": [108],
        "confidence": 0.91,
        "diagnostics": {},
        "suggested_next_action": "اسأل عن خواص الماء.",
    }


def test_ask_ai_audio_response_shape(ask_ai_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def fake_ask_question(*_args, **_kwargs):
        return _fake_ask_result()

    async def fake_tts(answer_text: str, **_kwargs):
        assert "الماء" in answer_text
        return {
            "audio_url": "/media/uploads/audio/output/answer_test.mp3",
            "audio_status": "ready",
            "audio_error": None,
            "media_block": {
                "type": "audio",
                "content": "إجابة صوتية مولدة من النص النهائي.",
                "url": "/media/uploads/audio/output/answer_test.mp3",
                "metadata": {"provider": "elevenlabs"},
            },
        }

    monkeypatch.setattr(chat_service, "ask_question", fake_ask_question)
    monkeypatch.setattr(chat_service, "synthesize_ask_answer_audio", fake_tts)

    response = ask_ai_client.post(
        "/api/v1/ai/ask",
        json={
            "question": "ما هو الماء؟",
            "answer_format": "audio",
            "subject": "chemistry",
            "grade": "9",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "audio"
    assert payload["answer"]
    assert payload["audio_url"] == "/media/uploads/audio/output/answer_test.mp3"
    assert payload["audio_status"] == "ready"
    assert payload["sources"][0]["page_number"] == 108
    assert payload["sources"][0]["source_type"] == "textbook"
    assert payload["sources"][0]["unit_id"] == "unit_04"
    assert payload["sources"][0]["lesson_id"] == "unit_04_lesson_01"
    assert payload["sources"][0]["quality_status"] == "ready"
    assert payload["sources"][0]["reviewed_metadata_version"] == "2026-06-reviewed-v1"
    assert payload["media_blocks"][0]["type"] == "audio"


def test_ask_ai_audio_tts_failure_keeps_text(ask_ai_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def fake_ask_question(*_args, **_kwargs):
        return _fake_ask_result()

    async def fake_tts(*_args, **_kwargs):
        return {
            "audio_url": None,
            "audio_status": "failed",
            "audio_error": {"code": "AUDIO_PROVIDER_NOT_CONFIGURED", "message": "ELEVENLABS_API_KEY is required."},
            "media_block": None,
        }

    monkeypatch.setattr(chat_service, "ask_question", fake_ask_question)
    monkeypatch.setattr(chat_service, "synthesize_ask_answer_audio", fake_tts)

    response = ask_ai_client.post(
        "/api/v1/ai/ask",
        json={
            "question": "ما هو الماء؟",
            "answer_format": "audio",
            "subject": "chemistry",
            "grade": "9",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "audio"
    assert payload["answer"]
    assert payload["audio_url"] is None
    assert payload["audio_status"] == "failed"
    assert payload["diagnostics"]["audio_error"]["code"] == "AUDIO_PROVIDER_NOT_CONFIGURED"
