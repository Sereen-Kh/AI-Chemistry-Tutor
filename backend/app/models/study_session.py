"""Persistent student study-session lifecycle."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class StudySession(Base, TimestampMixin):
    """Server-owned timer and lifecycle for studying one curriculum lesson."""

    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'paused', 'completed', 'abandoned')",
            name="ck_study_sessions_status",
        ),
        Index("study_sessions_user_status_idx", "user_id", "status"),
        Index("study_sessions_user_lesson_created_idx", "user_id", "lesson_id", "created_at"),
        Index(
            "uq_study_sessions_user_lesson_open",
            "user_id",
            "lesson_id",
            unique=True,
            postgresql_where=text("status IN ('running', 'paused')"),
            sqlite_where=text("status IN ('running', 'paused')"),
        ),
        Index(
            "uq_study_sessions_user_running",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
            sqlite_where=text("status = 'running'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    study_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="running", index=True)
    planned_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    elapsed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="study_sessions")
    lesson = relationship("Lesson", back_populates="study_sessions")
    study_plan = relationship("StudyPlan", back_populates="study_sessions")
