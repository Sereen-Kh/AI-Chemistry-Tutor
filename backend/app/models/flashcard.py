"""Flashcard deck, card, and spaced-repetition models."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class FlashcardDeck(Base, TimestampMixin):
    """A user-owned group of generated or manually curated flashcards."""

    __tablename__ = "flashcard_decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    description_ar: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scope_type: Mapped[str] = mapped_column(String(40), default="lesson", index=True, nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="book_rag", nullable=False)

    user = relationship("User", back_populates="flashcard_decks")
    cards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")


class Flashcard(Base, TimestampMixin):
    """A single learning card connected to curriculum and source evidence."""

    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    deck_id: Mapped[int | None] = mapped_column(
        ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Legacy fields kept for compatibility with the old API and seed data.
    front_ar: Mapped[str] = mapped_column(Text, nullable=False)
    back_ar: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(30), default="system", nullable=False)

    card_type: Mapped[str] = mapped_column(String(40), default="term_definition", index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", index=True, nullable=False)
    front_text_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    back_text_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    hint_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str] = mapped_column(Text, default="", nullable=False)
    technical_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    explanation_ar: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_chunk_ids: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    deck = relationship("FlashcardDeck", back_populates="cards")
    topic = relationship("Topic", back_populates="flashcards")
    progress_records = relationship(
        "FlashcardProgress", back_populates="flashcard", cascade="all, delete-orphan"
    )

    @property
    def effective_front_ar(self) -> str:
        return self.front_text_ar or self.front_ar

    @property
    def effective_back_ar(self) -> str:
        return self.back_text_ar or self.back_ar


class FlashcardProgress(Base, TimestampMixin):
    """Per-user spaced-repetition review state for a flashcard."""

    __tablename__ = "flashcard_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    flashcard_id: Mapped[int] = mapped_column(
        ForeignKey("flashcards.id", ondelete="CASCADE"), index=True
    )

    # Legacy fields kept for existing clients.
    mastered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_review_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="new", index=True, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="flashcard_progress")
    flashcard = relationship("Flashcard", back_populates="progress_records")
