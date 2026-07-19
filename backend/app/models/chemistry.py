"""Chemistry curriculum models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import TimestampMixin


lesson_topics = Table(
    "lesson_topics",
    Base.metadata,
    Column("lesson_id", ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
    Column("order", Integer, nullable=False, default=0),
)


class Element(Base):
    """Periodic table element reference data."""

    __tablename__ = "elements"

    atomic_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(4), unique=True, index=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(80), nullable=False)
    name_en: Mapped[str] = mapped_column(String(80), nullable=False)
    atomic_mass: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group: Mapped[int | None] = mapped_column(Integer, nullable=True)
    electron_configuration: Mapped[str | None] = mapped_column(Text, nullable=True)


class Unit(Base, TimestampMixin):
    """Top-level textbook unit (وحدة) containing ordered chapters."""

    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("unit_number", name="uq_units_unit_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(80), nullable=True)

    chapters = relationship("Chapter", back_populates="unit", order_by="Chapter.order")
    rag_chunks = relationship("RagChunk", back_populates="unit")


class Chapter(Base, TimestampMixin):
    """Ordered curriculum chapter."""

    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(80), nullable=True)

    unit = relationship("Unit", back_populates="chapters")
    lessons = relationship(
        "Lesson",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Lesson.order",
    )
    textbook_chunks = relationship("TextbookChunk", back_populates="chapter")
    rag_chunks = relationship("RagChunk", back_populates="chapter")


class Lesson(Base, TimestampMixin):
    """Lesson content within a chapter."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_ar: Mapped[str] = mapped_column(Text, default="", nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    chapter = relationship("Chapter", back_populates="lessons")
    topics = relationship(
        "Topic",
        secondary=lesson_topics,
        back_populates="lessons",
        order_by="Topic.order",
    )
    progress_records = relationship("LessonProgress", back_populates="lesson", cascade="all, delete-orphan")
    study_sessions = relationship("StudySession", back_populates="lesson")
    reels = relationship("Reel", back_populates="lesson", cascade="all, delete-orphan")
    rag_chunks = relationship("RagChunk", back_populates="lesson")


class LessonProgress(Base):
    """Per-user lesson completion state."""

    __tablename__ = "lesson_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="progress_records")
