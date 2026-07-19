"""User API schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.enums import ExplanationMethod, LearningMode, StudentInterest, TeachingLevel, TeachingStyle


class UserPublicResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    grade: str
    subject: str
    teaching_style: TeachingStyle
    answer_format: LearningMode
    teaching_level: TeachingLevel
    explanation_method: ExplanationMethod
    learning_modes: list[LearningMode]
    student_interests: list[StudentInterest]
    language: str
    xp: int
    level: int
    streak_days: int
    email_verified: bool
    learning_memory_enabled: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    teaching_style: TeachingStyle | None = None
    answer_format: LearningMode | None = None
    teaching_level: TeachingLevel | None = None
    explanation_method: ExplanationMethod | None = None
    learning_modes: list[LearningMode] | None = None
    student_interests: list[str] | None = None
    language: str | None = None
