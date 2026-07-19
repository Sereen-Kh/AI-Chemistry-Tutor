"""Versioned dashboard aggregate API schemas."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


LessonStatus = Literal["not_started", "in_progress", "completed"]
WeakTopicsState = Literal["ready", "insufficient_evidence"]
EvidenceLevel = Literal["limited", "established"]
MissionKind = Literal[
    "overdue_lesson",
    "today_lesson",
    "due_flashcards",
    "next_lesson",
    "create_plan",
]


class DashboardLessonSummary(BaseModel):
    id: int | None = None
    title_ar: str
    chapter_id: int | None = None
    chapter_title_ar: str | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    duration_min: int = 10
    status: LessonStatus = "not_started"
    scheduled_date: date | None = None
    # Deprecated compatibility projection. Unmeasured progress remains null.
    progress: int | None = Field(default=None, ge=0, le=100)


class DashboardTopicSummary(BaseModel):
    topic_id: int
    title_ar: str
    accuracy_percent: float = Field(ge=0, le=100)
    answered_questions: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    last_evidence_at: datetime | None = None
    evidence_level: EvidenceLevel
    reason: str
    action_url: str
    # Deprecated compatibility projection for older clients.
    best_quiz_score: float | None = Field(default=None, ge=0, le=100)


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


class DashboardCurriculumProgress(BaseModel):
    total_lessons: int = Field(ge=0)
    completed_lessons: int = Field(ge=0)
    percent: int | None = Field(default=None, ge=0, le=100)


class DashboardPlanLessonSummary(BaseModel):
    id: int
    title_ar: str
    scheduled_date: date | None = None
    status: Literal["not_started", "in_progress", "completed", "skipped", "overdue"]
    estimated_minutes: int = Field(default=0, ge=0)


class DashboardActivePlanProgress(BaseModel):
    plan_id: int
    total_scheduled_lessons: int = Field(ge=0)
    completed_lessons: int = Field(ge=0)
    in_progress_lessons: int = Field(ge=0)
    overdue_lessons: int = Field(ge=0)
    percent: int | None = Field(default=None, ge=0, le=100)
    next_lesson: DashboardPlanLessonSummary | None = None


class DashboardPrimaryMission(BaseModel):
    kind: MissionKind
    title_ar: str
    description_ar: str
    action_label_ar: str
    action_url: str
    reason_code: str
    lesson_id: int | None = None
    study_plan_id: int | None = None


class DashboardDataQuality(BaseModel):
    has_curriculum_data: bool
    has_lesson_progress: bool
    has_active_study_plan: bool
    has_plan_items: bool
    has_quiz_evidence: bool
    has_weak_topic_evidence: bool
    weak_topic_answer_count: int = Field(ge=0)
    weekly_xp_available: bool = False


class DashboardResponse(BaseModel):
    semantics_version: Literal["dashboard-progress-v1"] = "dashboard-progress-v1"
    generated_at: datetime
    user_id: int
    student_name: str
    xp: int
    level: int
    streak_days: int
    curriculum_progress: DashboardCurriculumProgress
    active_plan_progress: DashboardActivePlanProgress | None = None
    primary_mission: DashboardPrimaryMission
    weak_topics_state: WeakTopicsState
    continue_lesson: DashboardLessonSummary | None = None
    weak_topics: list[DashboardTopicSummary] = Field(default_factory=list)
    due_flashcards: DashboardFlashcardSummary = Field(default_factory=DashboardFlashcardSummary)
    next_quiz: DashboardQuizSummary | None = None
    study_plan: DashboardStudyPlanSummary | None = None
    notifications: DashboardNotificationSummary = Field(default_factory=DashboardNotificationSummary)
    quick_tools: list[dict[str, str]] = Field(default_factory=list)
    data_quality: DashboardDataQuality

    # Deprecated compatibility projections retained for one release.
    overall_progress: int | None = Field(default=None, ge=0, le=100)
    today_mission: str
    current_streak: int = 0
    lesson_progress_percentage: int | None = Field(default=None, ge=0, le=100)
    flashcards_due_count: int = 0
    weekly_xp: int | None = None
