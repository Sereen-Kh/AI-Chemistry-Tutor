"""Models for the Reminder Notification System."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Notification(Base, TimestampMixin):
    """System and study plan reminder notifications delivered to a user."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_status_scheduled", "user_id", "status", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # study_reminder, exam_countdown, overdue_lesson, flashcards_due, quiz_reminder, weak_topic, system
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    title_ar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="unread", nullable=False)  # unread, read, archived
    priority: Mapped[str] = mapped_column(String(30), default="normal", nullable=False)  # low, normal, high, urgent
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="notifications")


class NotificationPreference(Base, TimestampMixin):
    """User-specific settings and switches for notifications."""

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_study_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_study_reminder_time: Mapped[str] = mapped_column(String(10), default="08:00", nullable=False)
    exam_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    flashcards_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    overdue_lesson_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weak_topic_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(10), default="22:00", nullable=False)
    quiet_hours_end: Mapped[str] = mapped_column(String(10), default="07:00", nullable=False)
    # Legacy aliases kept for existing API clients and tests.
    exam_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lesson_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminder_time_local: Mapped[str] = mapped_column(String(10), default="08:00", nullable=False)  # HH:MM format
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    user = relationship("User", back_populates="notification_preference")


class ReminderEvent(Base, TimestampMixin):
    """Schedule logs for upcoming push/in-app reminders to avoid duplicate alerts."""

    __tablename__ = "reminder_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_type",
            "source_id",
            "reminder_type",
            name="uq_reminder_event_user_source_type",
        ),
        Index("ix_reminder_events_status_scheduled", "status", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)  # exam, lesson
    source_id: Mapped[str] = mapped_column(String(50), nullable=False)  # target exam/lesson identifier
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. 7_days_before, 30_minutes_before
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending, sent, skipped, failed
    notification_id: Mapped[Optional[int]] = mapped_column(ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True)

    user = relationship("User", back_populates="reminder_events")
    notification = relationship("Notification")
