"""User API schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserPublicResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    grade: str
    subject: str
    teaching_style: str
    answer_format: str
    language: str
    xp: int
    level: int
    streak_days: int
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    teaching_style: str | None = None
    answer_format: str | None = None
    language: str | None = None
