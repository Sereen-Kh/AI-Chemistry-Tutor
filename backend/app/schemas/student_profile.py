"""Student profile API schemas."""

from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import TeachingStyle


class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    grade: str
    subject: str
    learning_style: TeachingStyle
    preferred_language: str
    goals: str | None = None
    target_exam_date: date | None = None
    metadata_json: dict | list | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudentProfileUpsertRequest(BaseModel):
    grade: str = "grade_9"
    subject: str = "chemistry"
    learning_style: TeachingStyle = TeachingStyle.REAL_LIFE_EXAMPLES
    preferred_language: str = "ar"
    goals: str | None = None
    target_exam_date: date | None = None
    metadata_json: dict | list | None = None
