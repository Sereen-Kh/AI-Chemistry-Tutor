"""Pydantic schemas for authentication."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import LearningMode, TeachingStyle


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
    teaching_style: TeachingStyle = TeachingStyle.REAL_LIFE_EXAMPLES
    answer_format: LearningMode = LearningMode.TEXT
    language: str = "ar"
    interest_ids: list[int] = []


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
    language: str
    xp: int
    level: int
    streak_days: int
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
