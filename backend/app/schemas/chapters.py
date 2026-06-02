"""Chapter API schemas."""

from datetime import datetime

from pydantic import BaseModel


class ChapterResponse(BaseModel):
    id: int
    title_ar: str
    title_en: str | None = None
    description_ar: str | None = None
    order: int
    difficulty: int
    icon: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChapterCreateRequest(BaseModel):
    title_ar: str
    title_en: str | None = None
    description_ar: str | None = None
    order: int = 0
    difficulty: int = 1
    icon: str | None = None


class ChapterUpdateRequest(BaseModel):
    title_ar: str | None = None
    title_en: str | None = None
    description_ar: str | None = None
    order: int | None = None
    difficulty: int | None = None
    icon: str | None = None
