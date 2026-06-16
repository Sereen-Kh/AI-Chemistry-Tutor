"""Homework solver API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class HomeworkSolveTextRequest(BaseModel):
    problem_text: str = Field(..., min_length=1)
    topic_id: int | None = None


class HomeworkSolveImageRequest(BaseModel):
    image_path: str = Field(..., min_length=1)
    topic_id: int | None = None


class HomeworkResponse(BaseModel):
    id: int
    user_id: int
    topic_id: int | None = None
    image_url: str | None = None
    problem_text: str
    extracted_text: str | None = None
    solution: str
    source_chunks: list | dict | None = None
    confidence_score: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HomeworkUploadResponse(BaseModel):
    homework_id: int
    image_url: str
    image_path: str
    filename: str
    content_type: str | None = None
