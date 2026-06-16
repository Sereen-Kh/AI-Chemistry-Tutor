"""Dashboard aggregate API schemas."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class DashboardLessonSummary(BaseModel):
    id: int | None = None
    title_ar: str
    chapter_id: int | None = None
    chapter_title_ar: str | None = None
    progress: int = Field(default=0, ge=0, le=100)
    duration_min: int = 10
    status: str = "not_started"


class DashboardTopicSummary(BaseModel):
    topic_id: int | None = None
    title_ar: str
    best_quiz_score: float = 0.0
    reason: str


class DashboardQuizSummary(BaseModel):
    title: str
    topic_id: int | None = None
    score: int | None = None
    total: int | None = None


class DashboardFlashcardSummary(BaseModel):
    due_count: int = 0
    mastered_count: int = 0
    total_reviewed: int = 0


class DashboardNotificationSummary(BaseModel):
    unread_count: int = 0


class DashboardStudyPlanSummary(BaseModel):
    id: int | None = None
    exam_date: date | None = None
    days_to_exam: int | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardResponse(BaseModel):
    user_id: int
    student_name: str
    xp: int
    level: int
    streak_days: int
    overall_progress: int = Field(ge=0, le=100)
    today_mission: str
    continue_lesson: DashboardLessonSummary | None = None
    weak_topics: list[DashboardTopicSummary] = Field(default_factory=list)
    due_flashcards: DashboardFlashcardSummary = Field(default_factory=DashboardFlashcardSummary)
    next_quiz: DashboardQuizSummary | None = None
    study_plan: DashboardStudyPlanSummary | None = None
    notifications: DashboardNotificationSummary = Field(default_factory=DashboardNotificationSummary)
    quick_tools: list[dict[str, str]] = Field(default_factory=list)
    data_quality: dict[str, Any] = Field(default_factory=dict)
