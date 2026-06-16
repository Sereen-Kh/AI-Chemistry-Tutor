"""Topic model used by quizzes, flashcards, and progress."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Topic(Base, TimestampMixin):
    """Chemistry topic for assessments and review material."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(80), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)

    questions = relationship("Question", back_populates="topic", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="topic", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="topic", cascade="all, delete-orphan")
    user_progress = relationship("UserProgress", back_populates="topic", cascade="all, delete-orphan")
    homework_items = relationship("Homework", back_populates="topic")
    lessons = relationship("Lesson", secondary="lesson_topics", back_populates="topics", order_by="Lesson.order")
    rag_chunks = relationship("RagChunk", back_populates="topic")
    extracted_questions = relationship("ExtractedQuestion", back_populates="topic")
