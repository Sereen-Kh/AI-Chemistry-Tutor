"""OCR provider interface and implementations.

Gemini is the production default. Mistral and PaddleOCR are optional
alternatives, and OCRArena is intentionally limited to experimental/debug use.
"""

from __future__ import annotations

import asyncio
import base64
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

CHEMISTRY_OCR_PROMPT = """
You are a chemistry textbook OCR and extraction specialist.

Extract ALL educational content from this page. Do not summarize.

Return structured JSON with this schema:
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
      "answer_source": "page|unknown"
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
- Preserve Arabic text exactly.
- Preserve chemical notation such as H₂O, CO₂, NaCl.
- Convert unclear equations to best-readable text and add warning.
- If an answer is not visible on the page, set correct_answer=null.
- Do not invent answers.
- Do not skip diagrams, tables, or side boxes.
"""


@dataclass
class PageExtractionResult:
    """Structured result returned by every OCR provider."""

    page_number: int
    detected_language: str = "ar"
    sections: list[dict[str, Any]] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    diagrams: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    equations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provider: str = ""
    raw_text: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload for cache and ingestion."""
        return {
            "page_number": self.page_number,
            "detected_language": self.detected_language,
            "sections": self.sections,
            "questions": self.questions,
            "diagrams": self.diagrams,
            "tables": self.tables,
            "equations": self.equations,
            "warnings": self.warnings,
            "ocr_provider": self.provider,
            "raw_text": self.raw_text,
        }


class OCRProvider(ABC):
    """Base interface for page OCR providers."""

    name = "base"

    @property
    def is_configured(self) -> bool:
        """Return whether this provider can currently run."""
        return True

    @abstractmethod
    async def extract_page(self, image_path: str, page_number: int) -> PageExtractionResult:
        """Extract a rendered page image into structured educational content."""


class UnavailableOCRProvider(OCRProvider):
    """Safe provider used when the requested provider is not configured."""

    name = "unavailable"

    def __init__(self, requested_provider: str, reason: str):
        self.requested_provider = requested_provider
        self.reason = reason

    @property
    def is_configured(self) -> bool:
        return False

    async def extract_page(self, image_path: str, page_number: int) -> PageExtractionResult:
        return PageExtractionResult(
            page_number=page_number,
            provider=self.name,
            warnings=[
                f"OCR provider '{self.requested_provider}' is unavailable: {self.reason}.",
                "Vision extraction skipped; text-layer fallback will be used when available.",
            ],
        )


def parse_ocr_json(raw: str, page_number: int, provider: str) -> PageExtractionResult:
    """Parse structured OCR JSON with a safe fallback for plain-text responses."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return PageExtractionResult(
                page_number=int(data.get("page_number") or page_number),
                detected_language=data.get("detected_language") or "ar",
                sections=data.get("sections") or [],
                questions=data.get("questions") or [],
                diagrams=data.get("diagrams") or [],
                tables=data.get("tables") or [],
                equations=data.get("equations") or [],
                warnings=data.get("warnings") or [],
                provider=provider,
                raw_text=raw,
            )
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return PageExtractionResult(
        page_number=page_number,
        sections=[{"heading": None, "content": raw or "", "content_type": "mixed"}] if raw else [],
        warnings=["OCR response was not valid JSON."],
        provider=provider,
        raw_text=raw,
    )


class GeminiOCRProvider(OCRProvider):
    """Production OCR provider using Gemini multimodal extraction."""

    name = "gemini"

    @property
    def is_configured(self) -> bool:
        return bool(settings.effective_gemini_api_key)

    async def extract_page(self, image_path: str, page_number: int) -> PageExtractionResult:
        if not self.is_configured:
            return await UnavailableOCRProvider(self.name, "GEMINI_API_KEY is not configured").extract_page(
                image_path, page_number
            )

        def _call() -> str:
            import google.generativeai as genai
            from PIL import Image

            genai.configure(api_key=settings.effective_gemini_api_key)
            model = genai.GenerativeModel(settings.model_name)
            response = model.generate_content([CHEMISTRY_OCR_PROMPT, Image.open(image_path)])
            return response.text or ""

        raw = await asyncio.to_thread(_call)
        return parse_ocr_json(raw, page_number, self.name)


class MistralOCRProvider(OCRProvider):
    """Optional OCR provider using a Mistral vision-capable model."""

    name = "mistral"

    @property
    def is_configured(self) -> bool:
        return bool(settings.mistral_api_key)

    async def extract_page(self, image_path: str, page_number: int) -> PageExtractionResult:
        if not self.is_configured:
            return await UnavailableOCRProvider(self.name, "MISTRAL_API_KEY is not configured").extract_page(
                image_path, page_number
            )

        image_bytes = Path(image_path).read_bytes()
        image_data = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": "pixtral-12b-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CHEMISTRY_OCR_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{image_data}",
                        },
                    ],
                }
            ],
            "temperature": 0,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.mistral_api_key}"},
                json=payload,
            )
            response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        return parse_ocr_json(raw, page_number, self.name)


class OCRArenaProvider(OCRProvider):
    """Experimental/debug OCR provider.

    This is deliberately not selected by default and should not be used as the
    production OCR engine. It exists only for comparisons and troubleshooting.
    """

    name = "ocrarena"

    @property
    def is_configured(self) -> bool:
        return bool(settings.ocrarena_cookie and settings.ocrarena_public_base_url)

    async def extract_page(self, image_path: str, page_number: int) -> PageExtractionResult:
        if not self.is_configured:
            return await UnavailableOCRProvider(
                self.name,
                "OCRARENA_COOKIE and OCRARENA_PUBLIC_BASE_URL are required for debug use",
            ).extract_page(image_path, page_number)
        return PageExtractionResult(
            page_number=page_number,
            provider=self.name,
            warnings=[
                "OCRArena is configured only as a debug adapter in this backend.",
                "No production ingestion path depends on OCRArena.",
            ],
        )


class PaddleOCRProvider(OCRProvider):
    """Optional local OCR fallback using PaddleOCR when installed."""

    name = "paddleocr"

    @property
    def is_configured(self) -> bool:
        try:
            import paddleocr  # noqa: F401
        except Exception:
            return False
        return True

    async def extract_page(self, image_path: str, page_number: int) -> PageExtractionResult:
        if not self.is_configured:
            return await UnavailableOCRProvider(self.name, "paddleocr package is not installed").extract_page(
                image_path, page_number
            )

        def _call() -> str:
            from paddleocr import PaddleOCR

            ocr = PaddleOCR(use_angle_cls=True, lang="ar")
            result = ocr.ocr(image_path, cls=True)
            lines: list[str] = []
            for page in result or []:
                for item in page or []:
                    if len(item) >= 2 and item[1]:
                        lines.append(str(item[1][0]))
            return "\n".join(lines)

        text = await asyncio.to_thread(_call)
        return PageExtractionResult(
            page_number=page_number,
            sections=[{"heading": None, "content": text, "content_type": "mixed"}] if text else [],
            provider=self.name,
            raw_text=text,
            warnings=[] if text else ["PaddleOCR returned no text."],
        )


def get_ocr_provider(provider_name: str | None = None) -> OCRProvider:
    """Return the configured OCR provider. Gemini is the production default."""
    selected = (provider_name or settings.ocr_provider or "gemini").strip().lower()
    providers: dict[str, OCRProvider] = {
        "gemini": GeminiOCRProvider(),
        "mistral": MistralOCRProvider(),
        "ocrarena": OCRArenaProvider(),
        "paddleocr": PaddleOCRProvider(),
        "paddle": PaddleOCRProvider(),
    }
    provider = providers.get(selected)
    if provider is None:
        return UnavailableOCRProvider(selected, "unknown OCR provider")
    return provider
