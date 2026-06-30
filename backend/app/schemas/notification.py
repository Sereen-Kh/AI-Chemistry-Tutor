"""Schemas for notification entities."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


NotificationType = str
NotificationPriority = str
NotificationStatus = str


class NotificationBase(BaseModel):
    type: NotificationType
    title: str
    message: str
    title_ar: Optional[str] = None
    body_ar: Optional[str] = None
    status: NotificationStatus
    priority: NotificationPriority
    scheduled_for: datetime
    delivered_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    action_url: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
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
    push_enabled: bool = True
    email_enabled: bool = False
    in_app_enabled: bool = True
    daily_study_reminder_enabled: bool = True
    daily_study_reminder_time: str = "08:00"
    exam_reminder_enabled: bool = True
    flashcards_reminder_enabled: bool = True
    overdue_lesson_reminder_enabled: bool = True
    weak_topic_reminder_enabled: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    # Legacy fields retained for existing clients.
    exam_reminders_enabled: bool = True
    lesson_reminders_enabled: bool = True
    reminder_time_local: str = "08:00"
    timezone: str = "UTC"


class NotificationPreferenceUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    daily_study_reminder_enabled: Optional[bool] = None
    daily_study_reminder_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    exam_reminder_enabled: Optional[bool] = None
    flashcards_reminder_enabled: Optional[bool] = None
    overdue_lesson_reminder_enabled: Optional[bool] = None
    weak_topic_reminder_enabled: Optional[bool] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    # Legacy fields retained for existing clients.
    exam_reminders_enabled: Optional[bool] = None
    lesson_reminders_enabled: Optional[bool] = None
    reminder_time_local: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")  # HH:MM format
    timezone: Optional[str] = None


class NotificationCreate(BaseModel):
    type: NotificationType
    title_ar: str
    body_ar: str
    priority: NotificationPriority = "normal"
    scheduled_for: Optional[datetime] = None
    action_url: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str | int] = None
    metadata_json: Optional[dict[str, Any]] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
