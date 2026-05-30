"""Quiz question and attempt models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import TimestampMixin


class Question(Base, TimestampMixin):
    """A multiple-choice question linked to a chemistry topic."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    question_ar: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list | dict] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="seeded", nullable=False)

    topic = relationship("Topic", back_populates="questions")


class QuizAttempt(Base):
    """A completed quiz attempt and its scoring metadata."""

    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weak_topics: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="quiz_attempts")
    topic = relationship("Topic", back_populates="quiz_attempts")
