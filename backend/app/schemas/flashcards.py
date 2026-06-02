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
