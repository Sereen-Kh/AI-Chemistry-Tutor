"""Schemas for notification entities."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationBase(BaseModel):
    type: str
    title: str
    message: str
    status: str
    priority: str
    scheduled_for: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    action_url: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceBase(BaseModel):
    exam_reminders_enabled: bool = True
    lesson_reminders_enabled: bool = True
    push_enabled: bool = True
    email_enabled: bool = False
    in_app_enabled: bool = True
    reminder_time_local: str = "08:00"
    timezone: str = "UTC"


class NotificationPreferenceUpdate(BaseModel):
    exam_reminders_enabled: Optional[bool] = None
    lesson_reminders_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    reminder_time_local: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")  # HH:MM format
    timezone: Optional[str] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
