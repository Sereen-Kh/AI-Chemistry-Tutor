"""Pydantic schemas for chat endpoints."""

from datetime import datetime
from typing import Any

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


class ChatAskRequest(BaseModel):
    conversation_id: str | None = None
    parent_message_id: str | None = None
    question: str = Field(..., min_length=1)
    lesson_id: int | None = None
    topic_id: int | None = None
    source_types: list[str] = Field(default_factory=lambda: ["textbook"])
    preferred_answer_type: str = Field("text", pattern="^(auto|text|image|audio|video|mixed)$")
    answer_scope: str = Field("auto", pattern="^(auto|book_only|tutor_general)$")
    teaching_style: str | None = None
    action: str | None = None
    previous_question: str | None = None
    previous_answer: str | None = None
    previous_sources: list[dict[str, Any]] = Field(default_factory=list)
    previous_selected_chunks: list[dict[str, Any]] = Field(default_factory=list)


class ChatSourceResponse(BaseModel):
    chunk_id: int
    source_id: int
    source: str | None = None
    page_number: int | None = None
    content_type: str
    similarity_score: float


class AnswerBlock(BaseModel):
    type: str
    content: str = ""
    url: str | None = None
    page: int | None = None
    image_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnswerSourceBlock(BaseModel):
    book_id: str | None = None
    page: int | None = None
    chunk_id: int
    chunk_type: str
    score: float


class ChatAnswerResponse(BaseModel):
    answer: str
    answer_type: str = "text"
    route: str = "textbook_rag"
    grounding: str = "book"
    answer_scope: str = "auto"
    blocks: list[AnswerBlock] = Field(default_factory=list)
    sources: list[ChatSourceResponse] = Field(default_factory=list)
    source_blocks: list[AnswerSourceBlock] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list)
    confidence: float
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    suggested_next_action: str | None = None


class MessageFeedbackRequest(BaseModel):
    feedback: str = Field(..., pattern="^(up|down|helpful|not_helpful)$")
