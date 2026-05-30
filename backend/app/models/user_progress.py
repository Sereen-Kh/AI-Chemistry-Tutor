"""Aggregated per-topic user progress."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProgress(Base):
    """Aggregated topic stats for dashboards and weak-topic detection."""

    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    flashcards_mastered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quizzes_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_quiz_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="user_progress")
    topic = relationship("Topic", back_populates="user_progress")
