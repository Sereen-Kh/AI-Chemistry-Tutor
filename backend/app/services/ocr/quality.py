"""Extraction quality checks for document OCR/RAG ingestion."""

from __future__ import annotations

import re

from app.core.config import settings
from app.services.ocr.base import ExtractionQualityReport, PageExtractionResult

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def _result_text(result: PageExtractionResult) -> str:
    parts = [result.raw_markdown]
    parts.extend(section.content for section in result.sections if section.content)
    parts.extend(question.question_text for question in result.questions if question.question_text)
    parts.extend(diagram.description for diagram in result.diagrams if diagram.description)
    parts.extend(table.markdown for table in result.tables if table.markdown)
    parts.extend(equation.equation for equation in result.equations if equation.equation)
    if result.raw_text:
        parts.append(result.raw_text)
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def _arabic_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    arabic = sum(1 for char in letters if _ARABIC_RE.match(char))
    return round(arabic / len(letters), 4)


def evaluate_extraction_quality(
    result: PageExtractionResult,
    *,
    page_type: str | None = None,
    min_chars: int | None = None,
    min_completeness_score: float | None = None,
) -> ExtractionQualityReport:
    """Evaluate structured page extraction quality and fallback necessity."""
    text = _result_text(result)
    char_count = result.char_count if result.char_count is not None else len(text)
    raw_markdown_chars = len(result.raw_markdown or "")
    section_count = len(result.sections)
    question_count = len(result.questions)
    table_count = len(result.tables)
    equation_count = len(result.equations)
    diagram_count = len(result.diagrams)
    warning_count = len(result.warnings)
    min_page_chars = settings.gemini_min_page_chars if min_chars is None else min_chars
    min_score = settings.gemini_min_completeness_score if min_completeness_score is None else min_completeness_score

    issues: list[str] = []
    if not result.schema_valid:
        issues.append("invalid_schema")
    if not text.strip():
        issues.append("empty_output")
    if raw_markdown_chars == 0:
        issues.append("missing_raw_markdown")
    if char_count < min_page_chars:
        issues.append(f"very_low_char_count:{char_count}")
    if section_count == 0 and page_type in {"NEEDS_VISION", "MIXED_VISION", None}:
        issues.append("empty_sections")
    if (
        result.completeness_score is not None
        and min_score is not None
        and result.completeness_score < min_score
    ):
        issues.append(f"low_completeness_score:{result.completeness_score:.2f}")

    arabic_char_ratio = _arabic_ratio(text)
    if text.strip() and arabic_char_ratio < 0.2 and result.detected_language == "ar":
        issues.append(f"low_arabic_ratio:{arabic_char_ratio:.2f}")

    return ExtractionQualityReport(
        page_number=result.page_number,
        schema_valid=result.schema_valid,
        raw_markdown_chars=raw_markdown_chars,
        char_count=char_count,
        section_count=section_count,
        question_count=question_count,
        table_count=table_count,
        equation_count=equation_count,
        diagram_count=diagram_count,
        warning_count=warning_count,
        arabic_char_ratio=arabic_char_ratio,
        completeness_score=result.completeness_score,
        issues=issues,
        should_fallback=bool(issues),
    )
