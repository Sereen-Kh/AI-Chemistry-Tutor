"""Student profile API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import ExplanationMethod, LearningMode, StudentInterest, TeachingLevel, TeachingStyle


class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    grade: str
    subject: str
    learning_style: TeachingStyle
    teaching_level: TeachingLevel
    explanation_method: ExplanationMethod
    learning_modes: list[LearningMode]
    student_interests: list[StudentInterest]
    preferred_language: str
    goals: str | None = None
    target_exam_date: date | None = None
    metadata_json: dict | list | None = None
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudentProfileUpsertRequest(BaseModel):
    grade: str = "grade_9"
    subject: str = "chemistry"
    learning_style: TeachingStyle = TeachingStyle.REAL_LIFE_EXAMPLES
    teaching_level: TeachingLevel = TeachingLevel.STANDARD
    explanation_method: ExplanationMethod = ExplanationMethod.DIRECT
    learning_modes: list[LearningMode] = Field(default_factory=lambda: [LearningMode.TEXT])
    student_interests: list[StudentInterest] = Field(default_factory=list)
    preferred_language: str = "ar"
    goals: str | None = None
    target_exam_date: date | None = None
    metadata_json: dict | list | None = None
