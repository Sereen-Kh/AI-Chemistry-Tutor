"""Gemini-backed AI response service."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """
أنت EduMind، معلم كيمياء لطلاب الصف التاسع. أجب بالعربية الواضحة،
واستخدم معلومات الكتاب المدرسي عندما تكون متاحة. إذا لم تجد سياقاً
كافياً من الكتاب، قل ذلك بوضوح ثم قدم شرحاً عاماً مختصراً.
"""


async def get_ai_response(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
) -> str:
    """Generate a tutor answer from conversation messages."""
    if not settings.effective_gemini_api_key:
        last_message = messages[-1]["content"] if messages else ""
        return (
            "وضع الاختبار المحلي يعمل، لكن مفتاح Gemini غير مضبوط. "
            f"سؤالك كان: {last_message}"
        )

    def _call() -> str:
        import google.generativeai as genai

        genai.configure(api_key=settings.effective_gemini_api_key)
        model = genai.GenerativeModel(
            model_name=settings.model_name,
            system_instruction=system_prompt or DEFAULT_SYSTEM_PROMPT,
            generation_config={"temperature": 0.4, "max_output_tokens": 1024},
        )
        history = []
        for message in messages[:-1]:
            role = "user" if message["role"] == "user" else "model"
            history.append({"role": role, "parts": [message["content"]]})
        chat = model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"] if messages else "")
        return response.text

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:  # pragma: no cover - external API failure
        logger.exception("Gemini request failed")
        return f"حدث خطأ أثناء التواصل مع خدمة الذكاء الاصطناعي: {exc}"
