"""Cached AI audio reel model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Reel(Base):
    """Generated audio reel for a lesson."""

    __tablename__ = "reels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, index=True
    )
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    script: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visual_cues: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson", back_populates="reels")
