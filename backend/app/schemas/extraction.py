"""Public extraction schemas used by OCR and ingestion APIs."""

from app.services.ocr.base import (
    ExtractedDiagram,
    ExtractedEquation,
    ExtractedQuestionPayload,
    ExtractedSection,
    ExtractedTable,
    ExtractionQualityReport,
    PageExtractionResult,
)

__all__ = [
    "ExtractedDiagram",
    "ExtractedEquation",
    "ExtractedQuestionPayload",
    "ExtractedSection",
    "ExtractedTable",
    "ExtractionQualityReport",
    "PageExtractionResult",
]
