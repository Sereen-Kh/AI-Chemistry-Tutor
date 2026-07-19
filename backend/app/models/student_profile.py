"""Student profile model for personalization."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ExplanationMethod, LearningMode, TeachingLevel, TeachingStyle
from app.models.mixins import TimestampMixin
from app.services.onboarding_service import is_profile_onboarding_complete


class StudentProfile(Base, TimestampMixin):
    """Extended learning profile for a user."""

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    grade: Mapped[str] = mapped_column(String(50), default="grade_9", nullable=False)
    subject: Mapped[str] = mapped_column(String(80), default="chemistry", nullable=False)
    learning_style: Mapped[str] = mapped_column(String(80), default=TeachingStyle.REAL_LIFE_EXAMPLES, nullable=False)
    teaching_level: Mapped[str] = mapped_column(String(30), default=TeachingLevel.STANDARD.value, nullable=False)
    explanation_method: Mapped[str] = mapped_column(String(40), default=ExplanationMethod.DIRECT.value, nullable=False)
    learning_modes: Mapped[list[str]] = mapped_column(JSON, default=lambda: [LearningMode.TEXT.value], nullable=False)
    student_interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(8), default="ar", nullable=False)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="student_profile")

    @property
    def onboarding_completed(self) -> bool:
        return is_profile_onboarding_complete(self)

    @property
    def learning_memory_enabled(self) -> bool:
        """Return the opt-out preference stored in profile metadata."""
        metadata = self.metadata_json if isinstance(self.metadata_json, dict) else {}
        return metadata.get("learning_memory_enabled", True) is not False
