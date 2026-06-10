"""Document extraction provider package for EduMind ingestion."""

from app.services.ocr.base import ExtractionQualityReport, PageExtractionResult, UploadedDocument, VisionExtractionProvider
from app.services.ocr.gemini_provider import GeminiDocumentProvider, GeminiVisionProvider
from app.core.config import settings


class NoneVisionProvider(VisionExtractionProvider):
    """Stub provider used when OCR is explicitly disabled (ocr_provider='none').

    Any attempt to extract pages will raise RuntimeError.  Callers should check
    ``is_configured`` before calling ``extract_page`` or
    ``extract_page_from_pdf``.
    """

    name = "none"

    @property
    def is_configured(self) -> bool:  # type: ignore[override]
        return False

    async def extract_page(
        self,
        image_path: str,
        page_number: int,
        source_type: str,
    ) -> PageExtractionResult:
        raise RuntimeError(
            "OCR provider is set to 'none'. Set ocr_provider to 'gemini' to enable page extraction."
        )

    async def extract_page_from_pdf(
        self,
        uploaded_pdf: UploadedDocument,
        page_number: int,
        source_type: str,
        neighboring_pages: list[int] | None = None,
    ) -> PageExtractionResult:
        raise RuntimeError(
            "OCR provider is set to 'none'. Set ocr_provider to 'gemini' to enable page extraction."
        )


def get_vision_provider(provider_name: str | None = None) -> VisionExtractionProvider:
    """Return the configured document extraction provider.

    Supported values for *provider_name* / ``settings.ocr_provider``:

    * ``"gemini"`` / ``"gemini_document"`` / ``"gemini_vision"`` — use Gemini.
    * ``"none"`` — disable OCR; ingestion will fail fast on vision pages.
    """
    selected = (provider_name or settings.ocr_provider or "gemini").strip().lower()
    if selected == "none":
        return NoneVisionProvider()
    if selected not in {"gemini", "gemini_document", "gemini_vision"}:
        raise ValueError(
            f"Unsupported OCR provider '{selected}'. Valid values: 'gemini', 'none'."
        )
    return GeminiDocumentProvider()


__all__ = [
    "GeminiVisionProvider",
    "GeminiDocumentProvider",
    "NoneVisionProvider",
    "ExtractionQualityReport",
    "PageExtractionResult",
    "UploadedDocument",
    "VisionExtractionProvider",
    "get_vision_provider",
]
