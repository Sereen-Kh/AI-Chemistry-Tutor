"""Gemini-backed AI response service."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.gemini_client import get_gemini_client, tutor_generation_config

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """
أنت EduMind، معلم كيمياء لطلاب الصف التاسع. أجب بالعربية الواضحة،
واستخدم معلومات الكتاب المدرسي عندما تكون متاحة. إذا لم تجد سياقاً
كافياً من الكتاب، قل ذلك بوضوح ثم قدم شرحاً عاماً مختصراً.
"""


class AIServiceError(RuntimeError):
    """Base exception for model generation failures."""


class AIQuotaExceededError(AIServiceError):
    """Raised when Gemini refuses a request because quota or rate limit is exhausted."""


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc)
    return any(
        marker in text
        for marker in (
            "429",
            "RESOURCE_EXHAUSTED",
            "quota",
            "Quota",
            "rate-limit",
            "rate limit",
            "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
        )
    )


def _message_contents(messages: list[dict[str, str]]):
    from google.genai import types

    contents = []
    for message in messages:
        role = "model" if message.get("role") in {"assistant", "model"} else "user"
        text = (message.get("content") or "").strip()
        if not text:
            continue
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    if not contents:
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text="ابدأ المحادثة.")]))
    return contents


async def get_ai_response(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    raise_on_error: bool = False,
) -> str:
    """Generate a tutor answer from conversation messages."""
    if not settings.effective_gemini_api_key:
        last_message = messages[-1]["content"] if messages else ""
        return (
            "وضع الاختبار المحلي يعمل، لكن مفتاح Gemini غير مضبوط. "
            f"سؤالك كان: {last_message}"
        )

    def _call() -> str:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=settings.model_name,
            contents=_message_contents(messages),
            config=tutor_generation_config(system_prompt or DEFAULT_SYSTEM_PROMPT),
        )
        return response.text or ""

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:  # pragma: no cover - external API failure
        logger.exception("Gemini request failed")
        if _is_quota_error(exc):
            if raise_on_error:
                raise AIQuotaExceededError("Gemini quota or rate limit was exceeded.") from exc
            return (
                "وصلت خدمة Gemini إلى حد الاستخدام المؤقت أو اليومي. "
                "أعد المحاولة لاحقاً أو استخدم إجابة المصادر المحلية المتاحة."
            )
        if raise_on_error:
            raise AIServiceError("Gemini request failed.") from exc
        return "تعذر الاتصال بخدمة الذكاء الاصطناعي حالياً. أعد المحاولة لاحقاً."
