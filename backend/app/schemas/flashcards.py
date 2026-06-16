"""Flashcard API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class FlashcardResponse(BaseModel):
    id: int
    topic_id: int
    front_ar: str
    back_ar: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FlashcardCreateRequest(BaseModel):
    topic_id: int
    front_ar: str = Field(..., min_length=1)
    back_ar: str = Field(..., min_length=1)
    created_by: str = "manual"


class FlashcardReviewRequest(BaseModel):
    quality: int = Field(..., ge=0, le=5)


class FlashcardGenerateRequest(BaseModel):
    topic_id: int | None = None
    lesson_id: int | None = None
    source_text: str | None = None
    limit: int = Field(default=8, ge=1, le=30)
    created_by: str = "generated"


class FlashcardProgressResponse(BaseModel):
    id: int
    user_id: int
    flashcard_id: int
    mastered: bool
    review_count: int
    ease_factor: float
    interval_days: int
    next_review_at: date | None = None
    last_reviewed: datetime | None = None

    model_config = {"from_attributes": True}


class FlashcardDueResponse(BaseModel):
    id: int
    topic_id: int
    front_ar: str
    back_ar: str
    created_by: str
    mastered: bool = False
    review_count: int = 0
    ease_factor: float = 2.5
    interval_days: int = 0
    next_review_at: date | None = None
    last_reviewed: datetime | None = None

    model_config = {"from_attributes": True}
