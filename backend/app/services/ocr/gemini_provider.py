"""Gemini Vision provider for chemistry textbook page understanding."""

from __future__ import annotations

import asyncio
import json

from PIL import Image
from pydantic import ValidationError

from app.core.config import settings
from app.services.ocr.base import PageExtractionResult, VisionExtractionProvider

GEMINI_VISION_PROMPT = """
You are a chemistry textbook vision extraction specialist.

Extract ALL educational content from this page. Do not summarize.
Return valid JSON only, with this schema:
{
  "page_number": number,
  "detected_language": "ar",
  "sections": [
    {
      "heading": string | null,
      "content": string,
      "content_type": "text|table|diagram|equation|example|exercise|answer_key|mixed"
    }
  ],
  "questions": [
    {
      "question_text": string,
      "question_type": "multiple_choice|true_false|short_answer|calculation|essay|unknown",
      "options": array | null,
      "correct_answer": string | null,
      "explanation": string | null,
      "answer_source": "page|answer_key|unknown"
    }
  ],
  "diagrams": [
    {
      "title": string | null,
      "description": string,
      "labels": array,
      "related_text": string | null
    }
  ],
  "tables": [
    {
      "title": string | null,
      "markdown": string
    }
  ],
  "equations": [
    {
      "equation": string,
      "description": string | null
    }
  ],
  "warnings": []
}

Rules:
- Preserve Arabic text exactly. Do not transliterate Arabic.
- Do not summarize and do not skip visible text.
- Preserve chemical notation such as H₂O, CO₂, NaCl.
- Preserve reaction notation such as 2H₂ + O₂ → 2H₂O.
- Extract all visible questions and exercises.
- Extract answer keys only if the answer is visible on this page.
- If an answer is not visible, set correct_answer=null and answer_source="unknown".
- Do not invent official answers.
- Describe diagrams clearly enough that RAG can answer questions about them later.
- Extract tables as markdown.
- Extract equations separately.
- Return JSON only.
"""


class GeminiVisionProvider(VisionExtractionProvider):
    """Primary and only MVP vision provider."""

    name = "gemini_vision"

    @property
    def is_configured(self) -> bool:
        return bool(settings.effective_gemini_api_key)

    async def extract_page(
        self,
        image_path: str,
        page_number: int,
        source_type: str,
    ) -> PageExtractionResult:
        if not self.is_configured:
            return PageExtractionResult(
                page_number=page_number,
                provider=self.name,
                warnings=["Gemini Vision is not configured. GEMINI_API_KEY is required for vision extraction."],
            )

        def _call() -> str:
            import google.generativeai as genai

            genai.configure(api_key=settings.effective_gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_vision_model)
            prompt = f"{GEMINI_VISION_PROMPT}\n\nsource_type={source_type}\npage_number={page_number}"
            response = model.generate_content([prompt, Image.open(image_path)])
            return response.text or ""

        raw = await asyncio.to_thread(_call)
        return parse_gemini_json(raw, page_number)


def parse_gemini_json(raw: str, page_number: int) -> PageExtractionResult:
    """Parse Gemini JSON with a conservative plain-text fallback."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data.setdefault("page_number", page_number)
            data["provider"] = "gemini_vision"
            data["raw_text"] = raw
            return PageExtractionResult.model_validate(data)
    except (TypeError, ValueError, json.JSONDecodeError, ValidationError):
        pass
    return PageExtractionResult(
        page_number=page_number,
        sections=[{"heading": None, "content": raw, "content_type": "mixed"}] if raw else [],
        warnings=["Gemini Vision response was not valid structured JSON."],
        provider="gemini_vision",
        raw_text=raw,
    )
