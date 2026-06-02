"""Vision extraction provider contracts for educational page understanding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ContentType = Literal["text", "table", "diagram", "equation", "example", "exercise", "answer_key", "mixed"]
QuestionType = Literal["multiple_choice", "true_false", "short_answer", "calculation", "essay", "unknown"]
AnswerSource = Literal["page", "answer_key", "generated", "unknown"]


class ExtractedSection(BaseModel):
    heading: str | None = None
    content: str
    content_type: ContentType = "text"


class ExtractedQuestionPayload(BaseModel):
    question_text: str
    question_type: QuestionType = "unknown"
    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    answer_source: AnswerSource = "unknown"


class ExtractedDiagram(BaseModel):
    title: str | None = None
    description: str
    labels: list[str] = Field(default_factory=list)
    related_text: str | None = None


class ExtractedTable(BaseModel):
    title: str | None = None
    markdown: str


class ExtractedEquation(BaseModel):
    equation: str
    description: str | None = None


class ExtractionQualityReport(BaseModel):
    """Structured extraction quality signals used for fallback routing and benchmarks."""

    page_number: int
    schema_valid: bool = True
    raw_markdown_chars: int = 0
    char_count: int = 0
    section_count: int = 0
    question_count: int = 0
    table_count: int = 0
    equation_count: int = 0
    diagram_count: int = 0
    warning_count: int = 0
    arabic_char_ratio: float = 0.0
    completeness_score: float | None = None
    issues: list[str] = Field(default_factory=list)
    should_fallback: bool = False


class PageExtractionResult(BaseModel):
    page_number: int
    detected_language: str = "ar"
    raw_markdown: str = ""
    sections: list[ExtractedSection] = Field(default_factory=list)
    questions: list[ExtractedQuestionPayload] = Field(default_factory=list)
    diagrams: list[ExtractedDiagram] = Field(default_factory=list)
    tables: list[ExtractedTable] = Field(default_factory=list)
    equations: list[ExtractedEquation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extraction_notes: str | None = None
    provider: str = "gemini_document"
    model_name: str | None = None
    schema_valid: bool = True
    char_count: int | None = None
    completeness_score: float | None = None
    quality_report: ExtractionQualityReport | None = None
    raw_text: str | None = None

    @model_validator(mode="after")
    def populate_raw_markdown_and_counts(self) -> "PageExtractionResult":
        if not self.raw_markdown:
            self.raw_markdown = self._derive_markdown()
        if self.char_count is None:
            self.char_count = len(self.raw_markdown)
        return self

    def _derive_markdown(self) -> str:
        parts: list[str] = []
        parts.extend(section.content for section in self.sections if section.content)
        parts.extend(question.question_text for question in self.questions if question.question_text)
        parts.extend(diagram.description for diagram in self.diagrams if diagram.description)
        parts.extend(table.markdown for table in self.tables if table.markdown)
        parts.extend(equation.equation for equation in self.equations if equation.equation)
        if self.raw_text:
            parts.append(self.raw_text)
        return "\n\n".join(part.strip() for part in parts if part and part.strip())

    def to_payload(self) -> dict:
        return self.model_dump()


class UploadedDocument(BaseModel):
    """Provider-neutral handle for a PDF uploaded to a model file service."""

    provider: str = "gemini"
    name: str
    uri: str
    mime_type: str = "application/pdf"
    display_name: str | None = None

    def to_payload(self) -> dict:
        return self.model_dump()


class VisionExtractionProvider(ABC):
    """Base interface for structured page vision extraction."""

    name = "vision"

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return whether this provider can currently run."""

    @abstractmethod
    async def extract_page(
        self,
        image_path: str,
        page_number: int,
        source_type: str,
    ) -> PageExtractionResult:
        """Extract a rendered page image into structured educational content."""

    async def upload_pdf(self, pdf_path: str) -> UploadedDocument | None:
        """Upload a source PDF once before page extraction if the provider supports it."""
        return None

    async def extract_page_from_pdf(
        self,
        uploaded_pdf: UploadedDocument,
        page_number: int,
        source_type: str,
        neighboring_pages: list[int] | None = None,
    ) -> PageExtractionResult:
        """Extract one page directly from an uploaded PDF handle."""
        raise NotImplementedError(f"{self.name} does not support uploaded PDF extraction.")
