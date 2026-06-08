import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    ConfigDict
)

from app.core.constants import (
    Gender,
    UserRole,
    SubscriptionStatus
)


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