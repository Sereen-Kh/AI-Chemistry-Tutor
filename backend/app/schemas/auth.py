"""Pydantic schemas for authentication."""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import ExplanationMethod, LearningMode, StudentInterest, TeachingLevel, TeachingStyle


class RegisterRequest(BaseModel):
    """Registration request.

    `name` is kept for backward compatibility with the original frontend.
    New clients should send `first_name` and `last_name`.
    """

    name: str | None = None
    first_name: str | None = None
    last_name: str | None = ""
    email: EmailStr
    password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def require_name(self):
        if not self.first_name and not self.name:
            raise ValueError("Either name or first_name is required")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InterestCategoryResponse(BaseModel):
    id: int
    key: str
    name_ar: str
    name_en: str | None = None
    icon: str | None = None
    display_order: int

    model_config = {"from_attributes": True}


class OnboardingRequest(BaseModel):
    grade: str = "grade_9"
    subject: str = "chemistry"
    teaching_style: TeachingStyle = TeachingStyle.REAL_LIFE_EXAMPLES
    answer_format: LearningMode = LearningMode.TEXT
    teaching_level: TeachingLevel = TeachingLevel.STANDARD
    explanation_method: ExplanationMethod = ExplanationMethod.DIRECT
    learning_modes: list[LearningMode] = Field(default_factory=lambda: [LearningMode.TEXT])
    student_interests: list[StudentInterest] = Field(default_factory=list)
    language: str = "ar"
    preferred_language: str | None = None
    goals: str | None = None
    target_exam_date: date | None = None
    interest_ids: list[int] = Field(default_factory=list)


class UserResponse(BaseModel):
    id: int
    name: str
    first_name: str
    last_name: str
    email: str
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
    preferred_language: str | None = None
    goals: str | None = None
    target_exam_date: date | None = None
    onboarding_completed: bool
    xp: int
    level: int
    streak_days: int
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
