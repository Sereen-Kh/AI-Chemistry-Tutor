"""Flashcard and spaced-repetition models."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Flashcard(Base, TimestampMixin):
    """A term/question and answer card for review."""

    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    front_ar: Mapped[str] = mapped_column(Text, nullable=False)
    back_ar: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(30), default="system", nullable=False)

    topic = relationship("Topic", back_populates="flashcards")
    progress_records = relationship(
        "FlashcardProgress", back_populates="flashcard", cascade="all, delete-orphan"
    )


class FlashcardProgress(Base):
    """Per-user SM-2 style flashcard review state."""

    __tablename__ = "flashcard_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    flashcard_id: Mapped[int] = mapped_column(
        ForeignKey("flashcards.id", ondelete="CASCADE"), index=True
    )
    mastered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_review_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="flashcard_progress")
    flashcard = relationship("Flashcard", back_populates="progress_records")
