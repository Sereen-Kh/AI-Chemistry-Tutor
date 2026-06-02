"""Student profile API schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    grade: str
    subject: str
    learning_style: str
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
    learning_style: str = "real-life"
    preferred_language: str = "ar"
    goals: str | None = None
    target_exam_date: date | None = None
    metadata_json: dict | list | None = None
