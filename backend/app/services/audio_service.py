"""Provider-based audio STT/TTS services for chat."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings


class AudioProviderError(RuntimeError):
    """Base class for audio provider failures."""

    code = "AUDIO_PROVIDER_ERROR"


class AudioProviderNotConfigured(AudioProviderError):
    code = "AUDIO_PROVIDER_NOT_CONFIGURED"


class AudioTranscriptionError(AudioProviderError):
    code = "TRANSCRIPTION_FAILED"


class AudioSynthesisError(AudioProviderError):
    code = "TTS_FAILED"


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, file_path: Path, *, language: str = "auto", content_type: str | None = None) -> str:
        raise NotImplementedError


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, *, voice_id: str, language: str = "auto") -> bytes:
        raise NotImplementedError


def _language_code(language: str | None) -> str | None:
    normalized = (language or "auto").strip().lower()
    if normalized == "ar":
        return "ara"
    if normalized == "en":
        return "eng"
    return None


class ElevenLabsSTTProvider(STTProvider):
    """ElevenLabs Scribe STT provider.

    Uses the official REST endpoint documented as POST /v1/speech-to-text.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.elevenlabs_api_key
        self.model_id = model_id or settings.elevenlabs_stt_model
        self.base_url = (base_url or settings.elevenlabs_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _ensure_configured(self) -> None:
        if not self.api_key:
            raise AudioProviderNotConfigured("ELEVENLABS_API_KEY is required for speech-to-text.")

    async def transcribe(self, file_path: Path, *, language: str = "auto", content_type: str | None = None) -> str:
        self._ensure_configured()
        data: dict[str, str] = {"model_id": self.model_id}
        lang = _language_code(language)
        if lang:
            data["language_code"] = lang
        files = {
            "file": (
                file_path.name,
                file_path.read_bytes(),
                content_type or "application/octet-stream",
            )
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/v1/speech-to-text",
                headers={"xi-api-key": self.api_key},
                data=data,
                files=files,
            )
        if response.status_code >= 400:
            raise AudioTranscriptionError(f"ElevenLabs STT failed with status {response.status_code}: {response.text[:300]}")
        payload: dict[str, Any] = response.json()
        transcript = str(payload.get("text") or "").strip()
        if not transcript:
            raise AudioTranscriptionError("ElevenLabs STT returned an empty transcript.")
        return transcript


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider using POST /v1/text-to-speech/{voice_id}."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.elevenlabs_api_key
        self.model_id = model_id or settings.elevenlabs_tts_model
        self.base_url = (base_url or settings.elevenlabs_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _ensure_configured(self, voice_id: str) -> None:
        if not self.api_key:
            raise AudioProviderNotConfigured("ELEVENLABS_API_KEY is required for text-to-speech.")
        if not voice_id:
            raise AudioProviderNotConfigured("ELEVENLABS_DEFAULT_VOICE_ID is required for text-to-speech.")

    async def synthesize(self, text: str, *, voice_id: str, language: str = "auto") -> bytes:
        self._ensure_configured(voice_id)
        payload: dict[str, Any] = {
            "text": text,
            "model_id": self.model_id,
        }
        lang = _language_code(language)
        if lang:
            payload["language_code"] = lang
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/v1/text-to-speech/{voice_id}",
                params={"output_format": "mp3_44100_128"},
                headers={
                    "xi-api-key": self.api_key,
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if response.status_code >= 400:
            raise AudioSynthesisError(f"ElevenLabs TTS failed with status {response.status_code}: {response.text[:300]}")
        if not response.content:
            raise AudioSynthesisError("ElevenLabs TTS returned empty audio.")
        return response.content


class AudioService:
    """Orchestrates STT/TTS without exposing provider details to chat flow."""

    def __init__(self, stt_provider: STTProvider | None = None, tts_provider: TTSProvider | None = None) -> None:
        self.stt_provider = stt_provider or ElevenLabsSTTProvider()
        self.tts_provider = tts_provider or ElevenLabsTTSProvider()

    async def transcribe_audio(self, file_path: Path, *, language: str = "auto", content_type: str | None = None) -> str:
        return await self.stt_provider.transcribe(file_path, language=language, content_type=content_type)

    async def synthesize_speech(self, text: str, *, voice_id: str | None = None, language: str = "auto") -> bytes:
        trimmed = text.strip()
        if not trimmed:
            raise AudioSynthesisError("Cannot synthesize empty text.")
        max_chars = max(1, int(settings.tts_max_chars_per_response))
        return await self.tts_provider.synthesize(trimmed[:max_chars], voice_id=voice_id or settings.elevenlabs_default_voice_id, language=language)


def audio_service_from_settings() -> AudioService:
    stt_provider = (settings.stt_provider or "elevenlabs").lower()
    tts_provider = (settings.tts_provider or "elevenlabs").lower()
    if stt_provider != "elevenlabs" or tts_provider != "elevenlabs":
        raise AudioProviderNotConfigured("Only the ElevenLabs audio provider is configured for the MVP.")
    return AudioService()
