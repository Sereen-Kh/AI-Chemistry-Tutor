"""Lesson API schemas."""

from datetime import datetime

from pydantic import BaseModel


class LessonResponse(BaseModel):
    id: int
    chapter_id: int
    title_ar: str
    title_en: str | None = None
    content_ar: str
    order: int
    difficulty: int
    duration_min: int
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


class LessonUpdateRequest(BaseModel):
    title_ar: str | None = None
    title_en: str | None = None
    content_ar: str | None = None
    order: int | None = None
    difficulty: int | None = None
    duration_min: int | None = None
