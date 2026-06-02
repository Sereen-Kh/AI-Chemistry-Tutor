from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

class StudyPlanBase(BaseModel):
    exam_date: date | None = None
    plan_json: dict | list | None = None
    status: str = "active"

class StudyPlanCreate(StudyPlanBase):
    pass

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
