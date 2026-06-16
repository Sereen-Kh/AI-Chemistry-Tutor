"""User and profile model."""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ExplanationMethod, LearningMode, TeachingLevel, TeachingStyle
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    """Application user with learning preferences stored on the user row."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    grade: Mapped[str] = mapped_column(String(50), default="grade_9", nullable=False)
    subject: Mapped[str] = mapped_column(String(50), default="chemistry", nullable=False)
    teaching_style: Mapped[str] = mapped_column(String(50), default=TeachingStyle.REAL_LIFE_EXAMPLES, nullable=False)
    answer_format: Mapped[str] = mapped_column(String(50), default=LearningMode.TEXT, nullable=False)
    teaching_level: Mapped[str] = mapped_column(String(30), default=TeachingLevel.STANDARD.value, nullable=False)
    explanation_method: Mapped[str] = mapped_column(String(40), default=ExplanationMethod.DIRECT.value, nullable=False)
    learning_modes: Mapped[list[str]] = mapped_column(JSON, default=lambda: [LearningMode.TEXT.value], nullable=False)
    student_interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ar", nullable=False)

    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")
    student_profile = relationship(
        "StudentProfile", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    lesson_progress = relationship("LessonProgress", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    flashcard_progress = relationship(
        "FlashcardProgress", back_populates="user", cascade="all, delete-orphan"
    )
    user_progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    homework_items = relationship("Homework", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    device_tokens = relationship("DeviceToken", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_preference = relationship("NotificationPreference", back_populates="user", cascade="all, delete-orphan", uselist=False)
    reminder_events = relationship("ReminderEvent", back_populates="user", cascade="all, delete-orphan")
    interactive_sessions = relationship("InteractiveSession", back_populates="user", cascade="all, delete-orphan")
    interactive_step_answers = relationship("StudentStepAnswer", back_populates="user", cascade="all, delete-orphan")
    misconception_events = relationship("MisconceptionEvent", back_populates="user", cascade="all, delete-orphan")
    skill_mastery = relationship("SkillMastery", back_populates="user", cascade="all, delete-orphan")

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
