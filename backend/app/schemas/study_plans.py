from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

class StudyPlanBase(BaseModel):
    exam_date: date | None = None
    plan_json: dict | list | None = None
    status: str = "active"

class StudyPlanCreate(StudyPlanBase):
    pass


class StudyPlanGenerateRequest(BaseModel):
    title: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    examDate: str | None = None
    lessonIds: list[str | int] = Field(default_factory=list)
    studyDays: list[str] = Field(default_factory=list)
    studyHoursByDay: dict[str, float | int | str] = Field(default_factory=dict)
    dailyStudyHours: float | int | str | None = None
    lessonDuration: float | int | str | None = None
    weeklyRest: str | None = None
    priority: str | None = None
    mode: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class StudyPlanUpdate(BaseModel):
    exam_date: date | None = None
    plan_json: dict | list | None = None
    status: str | None = None

class StudyPlanResponse(StudyPlanBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


StudyPlanLessonStatus = Literal["not_started", "in_progress", "completed", "skipped", "overdue"]
StudyPlanTrackStatus = Literal["ahead", "on_track", "behind"]


class StudyPlanProgressNextLesson(BaseModel):
    id: int
    title_ar: str
    scheduled_date: str | None = None
    status: StudyPlanLessonStatus


class StudyPlanUnitProgress(BaseModel):
    unit_id: int | None = None
    unit_title_ar: str
    total_lessons: int
    completed_lessons: int
    completion_percent: float


class StudyPlanScheduledLessonProgress(BaseModel):
    study_plan_item_id: int | None = None
    lesson_id: int
    lesson_title_ar: str
    unit_title_ar: str | None = None
    chapter_title_ar: str | None = None
    scheduled_date: str | None = None
    status: StudyPlanLessonStatus
    completion_percent: float
    estimated_minutes: int = 0


class StudyPlanProgressResponse(BaseModel):
    plan_id: int
    plan_title: str
    total_scheduled_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    not_started_lessons: int
    overdue_lessons: int
    skipped_lessons: int = 0
    completion_percent: float
    expected_percent: float
    track_status: StudyPlanTrackStatus
    next_lesson: StudyPlanProgressNextLesson | None = None
    unit_progress: list[StudyPlanUnitProgress] = Field(default_factory=list)
    scheduled_lessons: list[StudyPlanScheduledLessonProgress] = Field(default_factory=list)
