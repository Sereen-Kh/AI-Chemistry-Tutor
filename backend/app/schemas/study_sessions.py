"""Request and response contracts for persistent Study Sessions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


StudySessionStatus = Literal["running", "paused", "completed", "abandoned"]


class StudySessionCreate(BaseModel):
    lesson_id: int = Field(..., gt=0)
    study_plan_id: int | None = Field(default=None, gt=0)


class StudySessionResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    study_plan_id: int | None = None
    status: StudySessionStatus
    planned_minutes: int
    elapsed_seconds: int
    started_at: datetime
    last_heartbeat_at: datetime
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    abandoned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    server_time: datetime
    lesson_title_ar: str
    lesson_page_start: int | None = None
    lesson_page_end: int | None = None
    lesson_progress_updated: bool = False
    study_plan_updated: bool = False
    stale_reconciled: bool = False
