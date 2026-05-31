"""Vision extraction provider contracts for educational page understanding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

ContentType = Literal["text", "table", "diagram", "equation", "example", "exercise", "answer_key", "mixed"]
QuestionType = Literal["multiple_choice", "true_false", "short_answer", "calculation", "essay", "unknown"]
AnswerSource = Literal["page", "answer_key", "unknown"]


class ExtractedSection(BaseModel):
    heading: str | None = None
    content: str
    content_type: ContentType = "text"


class ExtractedQuestionPayload(BaseModel):
    question_text: str
    question_type: QuestionType = "unknown"
    options: list | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    answer_source: AnswerSource = "unknown"


class ExtractedDiagram(BaseModel):
    title: str | None = None
    description: str
    labels: list = Field(default_factory=list)
    related_text: str | None = None


class ExtractedTable(BaseModel):
    title: str | None = None
    markdown: str


class ExtractedEquation(BaseModel):
    equation: str
    description: str | None = None


class PageExtractionResult(BaseModel):
    page_number: int
    detected_language: str = "ar"
    sections: list[ExtractedSection] = Field(default_factory=list)
    questions: list[ExtractedQuestionPayload] = Field(default_factory=list)
    diagrams: list[ExtractedDiagram] = Field(default_factory=list)
    tables: list[ExtractedTable] = Field(default_factory=list)
    equations: list[ExtractedEquation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provider: str = "gemini_vision"
    raw_text: str | None = None

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
