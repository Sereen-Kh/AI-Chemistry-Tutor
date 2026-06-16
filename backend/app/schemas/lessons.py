"""Lesson API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.topics import TopicResponse


class LessonResponse(BaseModel):
    id: int
    chapter_id: int
    title_ar: str
    title_en: str | None = None
    content_ar: str
    order: int
    difficulty: int
    duration_min: int
    page_start: int | None = None
    page_end: int | None = None
    topics: list[TopicResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LessonCreateRequest(BaseModel):
    chapter_id: int
    title_ar: str
    title_en: str | None = None
    content_ar: str = ""
    order: int = 0
    difficulty: int = 1
    duration_min: int = 10
    page_start: int | None = None
    page_end: int | None = None


class LessonUpdateRequest(BaseModel):
    title_ar: str | None = None
    title_en: str | None = None
    content_ar: str | None = None
    order: int | None = None
    difficulty: int | None = None
    duration_min: int | None = None
    page_start: int | None = None
    page_end: int | None = None
