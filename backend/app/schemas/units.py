"""Unit and nested curriculum catalog schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.topics import TopicResponse


class LessonCatalogResponse(BaseModel):
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


class ChapterCatalogResponse(BaseModel):
    id: int
    unit_id: int | None = None
    title_ar: str
    title_en: str | None = None
    description_ar: str | None = None
    order: int
    difficulty: int
    icon: str | None = None
    lessons: list[LessonCatalogResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UnitResponse(BaseModel):
    id: int
    unit_number: int
    semester: int
    title_ar: str
    title_en: str | None = None
    description_ar: str | None = None
    order: int
    icon: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UnitCatalogResponse(UnitResponse):
    chapters: list[ChapterCatalogResponse] = Field(default_factory=list)
