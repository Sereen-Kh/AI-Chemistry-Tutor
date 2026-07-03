"""Flashcard API schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

FlashcardScopeType = Literal["lesson", "unit", "topic", "study_plan", "weak_topics", "custom"]
FlashcardDeckStatus = Literal["draft", "active", "archived"]
FlashcardDeckSource = Literal["ai_generated", "manual", "book_rag"]
FlashcardCardType = Literal[
    "term_definition",
    "concept_explanation",
    "equation_law",
    "calculation",
    "experiment_result",
    "compare_contrast",
    "reaction_balancing",
    "safety_rule",
    "image_based",
]
FlashcardDifficulty = Literal["easy", "medium", "hard", "mixed"]
FlashcardReviewRating = Literal["again", "hard", "good", "easy"]
FlashcardReviewStatus = Literal["new", "learning", "review", "mastered", "suspended"]


class FlashcardReviewStateResponse(BaseModel):
    id: int | None = None
    user_id: int | None = None
    flashcard_id: int
    status: FlashcardReviewStatus = "new"
    due_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    repetitions: int = 0
    lapses: int = 0
    ease_factor: float = 2.5
    interval_days: int = 0
    mastered: bool = False
    review_count: int = 0
    next_review_at: date | None = None
    last_reviewed: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class FlashcardResponse(BaseModel):
    id: int
    deck_id: int | None = None
    unit_id: int | None = None
    chapter_id: int | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    card_type: str = "term_definition"
    difficulty: str = "medium"
    front_ar: str
    back_ar: str
    front_text_ar: str | None = None
    back_text_ar: str | None = None
    hint_ar: str | None = None
    description_ar: str = ""
    technical_description: str = ""
    explanation_ar: str = ""
    source_page_start: int | None = None
    source_page_end: int | None = None
    source_chunk_ids: list | dict | None = None
    tags: list | dict | None = None
    metadata_json: dict | list | None = None
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime
    review: FlashcardReviewStateResponse | None = None

    model_config = {"from_attributes": True}


class FlashcardDeckResponse(BaseModel):
    id: int
    user_id: int
    title_ar: str
    description_ar: str
    scope_type: str
    scope_id: str | None = None
    status: str
    source: str
    total_cards: int = 0
    due_cards: int = 0
    new_cards: int = 0
    learning_cards: int = 0
    mastered_cards: int = 0
    overdue_cards: int = 0
    mastery_percent: int = 0
    cards: list[FlashcardResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FlashcardCreateRequest(BaseModel):
    topic_id: int | None = None
    deck_id: int | None = None
    front_ar: str = Field(..., min_length=1)
    back_ar: str = Field(..., min_length=1)
    hint_ar: str | None = None
    card_type: str = "term_definition"
    difficulty: str = "medium"
    description_ar: str = Field(default="تختبر هذه البطاقة فهماً كيميائياً من الدرس.", min_length=1)
    technical_description: str = Field(default="Manual flashcard.", min_length=1)
    explanation_ar: str = ""
    created_by: str = "manual"


class FlashcardDeckUpdateRequest(BaseModel):
    title_ar: str | None = None
    description_ar: str | None = None
    status: FlashcardDeckStatus | None = None


class FlashcardUpdateRequest(BaseModel):
    front_text_ar: str | None = None
    back_text_ar: str | None = None
    hint_ar: str | None = None
    description_ar: str | None = None
    technical_description: str | None = None
    explanation_ar: str | None = None
    difficulty: str | None = None
    card_type: str | None = None
    tags: list[str] | None = None


class FlashcardReviewRequest(BaseModel):
    rating: FlashcardReviewRating | None = None
    quality: int | None = Field(default=None, ge=0, le=5)

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: str | None) -> str | None:
        return value


class FlashcardGenerateRequest(BaseModel):
    scope_type: FlashcardScopeType = "lesson"
    scope_id: str | None = None
    lesson_ids: list[int] = Field(default_factory=list)
    topic_ids: list[int] = Field(default_factory=list)
    unit_ids: list[int] = Field(default_factory=list)
    cards_per_lesson: int = Field(default=4, ge=1, le=20)
    card_types: list[str] = Field(default_factory=lambda: ["term_definition", "concept_explanation"])
    difficulty: FlashcardDifficulty = "mixed"
    include_sources: bool = True
    title_ar: str | None = None
    description_ar: str | None = None

    # Backwards-compatible fields used by the previous frontend.
    topic_id: int | None = None
    lesson_id: int | None = None
    source_text: str | None = None
    limit: int = Field(default=8, ge=1, le=60)
    created_by: str = "generated"

    @field_validator("card_types")
    @classmethod
    def require_card_types(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("اختر نوع بطاقة واحداً على الأقل")
        return value


class FlashcardProgressSummaryResponse(BaseModel):
    total_cards: int
    due_today: int
    new_cards: int
    learning_cards: int
    mastered_cards: int
    overdue_cards: int
    mastery_percent: int


class FlashcardReviewResponse(BaseModel):
    card_id: int
    new_due_at: datetime | None
    status: FlashcardReviewStatus
    interval_days: int
    ease_factor: float
    repetitions: int
    lapses: int


class FlashcardReviewSessionCreateRequest(BaseModel):
    deck_id: int | None = None
    limit: int = Field(default=20, ge=1, le=100)


class FlashcardReviewSessionResponse(BaseModel):
    session_id: str
    deck_id: int | None = None
    total_cards: int
    cards: list[FlashcardResponse]


class FlashcardProgressResponse(FlashcardReviewStateResponse):
    """Legacy progress response shape kept for old callers."""


class FlashcardDueResponse(FlashcardResponse):
    mastered: bool = False
    review_count: int = 0
    ease_factor: float = 2.5
    interval_days: int = 0
    next_review_at: date | None = None
    last_reviewed: datetime | None = None
