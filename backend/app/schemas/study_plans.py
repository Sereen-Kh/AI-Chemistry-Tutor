from datetime import date, datetime
from typing import Any

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
    dailyStudyHours: float | None = None
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
