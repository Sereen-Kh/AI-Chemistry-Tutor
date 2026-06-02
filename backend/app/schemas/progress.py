"""Progress and achievement API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class LessonProgressUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(not_started|in_progress|completed)$")


class LessonProgressResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    status: str
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProgressResponse(BaseModel):
    id: int
    user_id: int
    topic_id: int
    flashcards_mastered: int
    quizzes_completed: int
    best_quiz_score: float
    last_activity: datetime | None = None

    model_config = {"from_attributes": True}


class AchievementResponse(BaseModel):
    id: int
    user_id: int
    name: str
    slug: str | None = None
    icon: str | None = None
    condition: str | None = None
    earned_at: datetime

    model_config = {"from_attributes": True}
