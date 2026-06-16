"""Pydantic schemas for the guided interactive chemistry solver."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InteractiveSourceReference(BaseModel):
    chunk_id: int
    page_number: int | None = None
    source_type: str
    content_type: str
    preview: str
    similarity_score: float | None = None


class InteractiveSessionCreate(BaseModel):
    problem_text: str = Field(..., min_length=1)
    topic_id: int | None = None
    source_types: list[str] | None = Field(default_factory=lambda: ["textbook", "solution_book"])


class InteractiveStepResponse(BaseModel):
    id: int
    session_id: int
    step_index: int
    step_key: str
    title_ar: str
    prompt_ar: str
    expected_answer_type: str
    expected_unit: str | None = None
    status: str
    hint_ar: str | None = None
    explanation_ar: str | None = None
    metadata_json: dict | list | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InteractiveSessionResponse(BaseModel):
    id: int
    user_id: int
    topic_id: int | None = None
    problem_text: str
    problem_type: str
    status: str
    current_step_index: int
    source_chunks: list[InteractiveSourceReference] = Field(default_factory=list)
    current_step: InteractiveStepResponse | None = None
    steps: list[InteractiveStepResponse] = Field(default_factory=list)
    final_answer: str | None = None
    weak_topics: list[str] = Field(default_factory=list)
    suggested_actions: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InteractiveAnswerSubmit(BaseModel):
    answer_text: str = Field(..., min_length=1)
    step_id: int | None = None


class InteractiveSessionSummaryResponse(BaseModel):
    session_id: int
    status: str
    final_answer: str
    step_summary: list[dict[str, Any]]
    sources: list[InteractiveSourceReference] = Field(default_factory=list)
    detected_weak_topics: list[str] = Field(default_factory=list)
    suggested_mini_quiz_action: dict[str, Any]
    suggested_flashcard_generation_action: dict[str, Any]


class InteractiveAnswerResponse(BaseModel):
    session_id: int
    step_id: int
    is_correct: bool
    feedback_ar: str
    misconception_type: str | None = None
    parsed_value: float | None = None
    parsed_unit: str | None = None
    current_step: InteractiveStepResponse | None = None
    next_step: InteractiveStepResponse | None = None
    session_status: str
    final_summary: InteractiveSessionSummaryResponse | None = None
