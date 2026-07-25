from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr
from app.core.constants import Gender, SubscriptionStatus, UserRole


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    gender: Gender


class UserRegister(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    gender: Gender | None = None


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserResponse(UserBase):
    id: uuid.UUID

    role: UserRole
    subscription_status: SubscriptionStatus

    is_active: bool

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )