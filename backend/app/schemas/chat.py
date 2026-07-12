"""Pydantic schemas for chat endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ExplanationMethod, LearningMode, StudentInterest, TeachingLevel


class SessionCreate(BaseModel):
    title: str | None = None
    lesson_id: int | None = None
    style: str | None = None


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    answer_text: str | None = None
    format: str
    feedback: str | None = None
    media_url: str | None = None
    latency_ms: int | None = None
    confidence: float | None = None
    answer_type: str | None = None
    route: str | None = None
    grounding: str | None = None
    input_type: str | None = None
    requested_return_type: str | None = None
    resolved_return_type: str | None = None
    text_content: str | None = None
    audio_input_url: str | None = None
    audio_transcript: str | None = None
    answer_audio_url: str | None = None
    transcription_status: str | None = None
    audio_status: str | None = None
    audio_provider: str | None = None
    tts_model: str | None = None
    stt_model: str | None = None
    voice_id: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    media_blocks: list[dict[str, Any]] = Field(default_factory=list)
    source_blocks: list[dict[str, Any]] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    suggested_next_action: str | None = None
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
    answer_scope: str = Field("auto", pattern="^(auto|book_only|tutor_general)$")
    source_types: list[str] | None = None
    teaching_style: str | None = None
    teaching_level: TeachingLevel | None = None
    explanation_method: ExplanationMethod | None = None
    learning_modes: list[LearningMode] | None = None
    student_interests: list[StudentInterest] | None = None
    action: str | None = None


class ChatAskRequest(BaseModel):
    conversation_id: str | None = None
    parent_message_id: str | None = None
    question: str | None = Field(default=None, min_length=1)
    message: str | None = Field(default=None, min_length=1)
    subject: str | None = None
    grade: str | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    source_types: list[str] | None = None
    preferred_answer_type: str = Field("text", pattern="^(auto|text|image|audio|video|mixed)$")
    answer_format: str | None = Field(default=None, pattern="^(auto|text|image|audio|video|mixed)$")
    answer_scope: str = Field("auto", pattern="^(auto|book_only|tutor_general)$")
    teaching_style: str | None = None
    teaching_level: TeachingLevel | None = None
    explanation_method: ExplanationMethod | None = None
    learning_modes: list[LearningMode] | None = None
    student_interests: list[StudentInterest] | None = None
    action: str | None = None
    previous_question: str | None = None
    previous_answer: str | None = None
    previous_sources: list[dict[str, Any]] = Field(default_factory=list)
    previous_selected_chunks: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_question_or_message(self) -> "ChatAskRequest":
        resolved = (self.question or self.message or "").strip()
        if not resolved:
            raise ValueError("question or message is required")
        self.question = resolved
        self.message = resolved
        if self.answer_format:
            self.preferred_answer_type = self.answer_format
        return self


class ChatSourceResponse(BaseModel):
    chunk_id: int
    source_id: int
    source: str | None = None
    source_type: str | None = None
    page_number: int | None = None
    content_type: str
    unit_id: int | str | None = None
    lesson_id: int | str | None = None
    quality_status: str | None = None
    quality_warning: str | None = None
    reviewed_metadata_version: str | None = None
    curriculum_metadata: dict[str, Any] | None = None
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
    source_type: str | None = None
    source_id: int | None = None
    unit_id: int | str | None = None
    lesson_id: int | str | None = None
    quality_status: str | None = None
    quality_warning: str | None = None
    reviewed_metadata_version: str | None = None
    curriculum_metadata: dict[str, Any] | None = None


class ChatAnswerResponse(BaseModel):
    answer: str
    answer_text: str = ""
    answer_type: str = "text"
    format: str = "text"
    audio_url: str | None = None
    audio_status: str = "not_required"
    route: str = "textbook_rag"
    grounding: str = "book"
    answer_scope: str = "auto"
    teaching_level: TeachingLevel = TeachingLevel.STANDARD
    explanation_method: ExplanationMethod = ExplanationMethod.DIRECT
    learning_modes: list[LearningMode] = Field(default_factory=lambda: [LearningMode.TEXT])
    student_interests: list[StudentInterest] = Field(default_factory=list)
    blocks: list[AnswerBlock] = Field(default_factory=list)
    sources: list[ChatSourceResponse] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    media_blocks: list[AnswerBlock] = Field(default_factory=list)
    source_blocks: list[AnswerSourceBlock] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list)
    confidence: float
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    suggested_next_action: str | None = None


class MessageFeedbackRequest(BaseModel):
    feedback: str = Field(..., pattern="^(up|down|helpful|not_helpful)$")
