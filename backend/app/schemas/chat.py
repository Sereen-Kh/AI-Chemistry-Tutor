"""Pydantic schemas for chat endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = None
    lesson_id: int | None = None
    style: str | None = None


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    format: str
    feedback: str | None = None
    media_url: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int | None = None
    title: str | None = None
    style: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    format: str = "text"
