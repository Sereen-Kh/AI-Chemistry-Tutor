"""Quiz and exam trainer API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class QuizGenerateRequest(BaseModel):
    topic_id: int | None = None
    lesson_id: int | None = None
    topic_ids: list[int] = Field(default_factory=list)
    lesson_ids: list[int] = Field(default_factory=list)
    source_type: str | None = None
    source: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    limit: int = Field(default=5, ge=1, le=30)
    question_count: int | None = Field(default=None, ge=1, le=30)
    question_types: list[str] = Field(default_factory=list)


class QuizQuestionResponse(BaseModel):
    id: int
    lesson_id: int | None = None
    topic_id: int | None = None
    question_text: str
    question_type: str
    options: list | dict | None = None
    page_number: int | None = None
    source_id: int | None = None
    difficulty: int | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    quality_status: str | None = None
    reviewed_metadata_version: str | None = None


class QuizGenerateResponse(BaseModel):
    questions: list[QuizQuestionResponse]
    generated: bool = False
    source: str = "database"


class QuizSubmitRequest(BaseModel):
    topic_id: int | None = None
    answers: dict[str, str]


class QuizSubmitResponse(BaseModel):
    attempt_id: int
    score: int
    total: int
    weak_topics: dict | list | None = None
    percentage: float = 0.0


class QuizAttemptResponse(BaseModel):
    id: int
    user_id: int
    topic_id: int
    score: int
    total: int
    answers: dict | None = None
    weak_topics: dict | list | None = None
    completed_at: datetime

    model_config = {"from_attributes": True}


class QuizRecommendationResponse(BaseModel):
    topic_id: int
    title_ar: str
    reason: str
    priority: int
