"""Gemini-only document extraction provider package for the MVP."""

from app.services.ocr.base import ExtractionQualityReport, PageExtractionResult, UploadedDocument, VisionExtractionProvider
from app.services.ocr.gemini_provider import GeminiDocumentProvider, GeminiVisionProvider
from app.core.config import settings


def get_vision_provider(provider_name: str | None = None) -> VisionExtractionProvider:
    """Return the MVP document extraction provider.

    The backend intentionally supports only Gemini document extraction for OCR/page
    understanding in the MVP so dry-run and production use the same code path.
    """
    selected = (provider_name or settings.ocr_provider or "gemini").strip().lower()
    if selected not in {"gemini", "gemini_document", "gemini_vision"}:
        raise ValueError("Gemini document extraction is the only supported OCR provider for the MVP.")
    return GeminiDocumentProvider()


__all__ = [
    "GeminiVisionProvider",
    "GeminiDocumentProvider",
    "ExtractionQualityReport",
    "PageExtractionResult",
    "UploadedDocument",
    "VisionExtractionProvider",
    "get_vision_provider",
]
