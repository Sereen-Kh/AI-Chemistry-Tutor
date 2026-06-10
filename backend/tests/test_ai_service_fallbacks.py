"""Regression tests for fast local fallback when Gemini is unavailable."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import ai_service
from app.services.chat_service import _answer_with_rag_fallback
from app.services.rag import RetrievedChunk


def test_gemini_quota_failure_enters_generation_cooldown(monkeypatch):
    calls = {"count": 0}

    class FakeModels:
        def generate_content(self, *args, **kwargs):
            raise RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded")

    def fake_client():
        calls["count"] += 1
        return SimpleNamespace(models=FakeModels())

    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(settings, "google_api_key", "")
    monkeypatch.setattr(settings, "gemini_tutor_generation_enabled", True)
    monkeypatch.setattr(settings, "gemini_failure_cooldown_seconds", 30)
    monkeypatch.setattr(ai_service, "get_gemini_client", fake_client)
    monkeypatch.setattr(ai_service, "_GEMINI_GENERATION_DISABLED_UNTIL", 0.0)
    monkeypatch.setattr(ai_service, "_GEMINI_GENERATION_DISABLED_REASON", "")

    with pytest.raises(ai_service.AIQuotaExceededError):
        asyncio.run(
            ai_service.get_ai_response(
                [{"role": "user", "content": "ما هي الحموض؟"}],
                system_prompt="أجب بالعربية.",
                raise_on_error=True,
            )
        )

    with pytest.raises(ai_service.AIServiceError):
        asyncio.run(
            ai_service.get_ai_response(
                [{"role": "user", "content": "ما هي الأسس؟"}],
                system_prompt="أجب بالعربية.",
                raise_on_error=True,
            )
        )

    assert calls["count"] == 1


def test_chat_rag_fallback_reports_quota_diagnostics(monkeypatch):
    async def fake_ai_response(*args, **kwargs):
        raise ai_service.AIQuotaExceededError("RESOURCE_EXHAUSTED")

    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(settings, "google_api_key", "")
    monkeypatch.setattr(ai_service, "get_ai_response", fake_ai_response)

    diagnostics = {}
    chunk = RetrievedChunk(
        id=1,
        source_id=1,
        content="تحذير دائما أضف الحمض إلى الماء.",
        source="كتاب الكيمياء",
        source_type="textbook",
        content_type="text",
        page_number=7,
        chapter_id=None,
        lesson_id=None,
        topic_id=None,
        metadata_json=None,
        similarity_score=0.92,
    )

    answer = asyncio.run(
        _answer_with_rag_fallback(
            messages=[{"role": "user", "content": "لماذا نضيف الحمض إلى الماء وليس العكس؟"}],
            question="لماذا نضيف الحمض إلى الماء وليس العكس؟",
            chunks=[chunk],
            system_prompt="أجب بالعربية.",
            diagnostics=diagnostics,
        )
    )

    assert "أضف الحمض إلى الماء" in answer
    assert diagnostics["gemini_available"] is False
    assert diagnostics["gemini_error"] == "RESOURCE_EXHAUSTED"
    assert diagnostics["fallback_used"] == "local_router"
