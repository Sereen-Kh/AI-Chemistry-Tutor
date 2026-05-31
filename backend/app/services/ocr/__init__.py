"""Gemini-only OCR/Vision provider package for the MVP."""

from app.services.ocr.base import PageExtractionResult, VisionExtractionProvider
from app.services.ocr.gemini_provider import GeminiVisionProvider
from app.core.config import settings


def get_vision_provider(provider_name: str | None = None) -> VisionExtractionProvider:
    """Return the MVP vision provider.

    The backend intentionally supports only Gemini Vision for OCR/page
    understanding in the MVP so dry-run and production use the same code path.
    """
    selected = (provider_name or settings.ocr_provider or "gemini").strip().lower()
    if selected not in {"gemini", "gemini_vision"}:
        raise ValueError("Gemini Vision is the only supported OCR/Vision provider for the MVP.")
    return GeminiVisionProvider()


__all__ = ["GeminiVisionProvider", "PageExtractionResult", "VisionExtractionProvider", "get_vision_provider"]
