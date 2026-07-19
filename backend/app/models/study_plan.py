"""Study plan model."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class StudyPlan(Base, TimestampMixin):
    """AI-generated study plan for a student's target exam date."""

    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    plan_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)

    user = relationship("User", back_populates="study_plans")
    study_sessions = relationship("StudySession", back_populates="study_plan")
