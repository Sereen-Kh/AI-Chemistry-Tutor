"""Content source and RAG chunk storage."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.database import Base
from app.models.mixins import TimestampMixin

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - optional dependency for SQLite dev
    Vector = None


def _embedding_type():
    if settings.database_url.startswith("postgres") and Vector is not None:
        return Vector(768)
    return JSON


class TextbookChunk(Base, TimestampMixin):
    """Legacy textbook-only chunk table kept for compatibility."""

    __tablename__ = "textbook_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(_embedding_type(), nullable=True)

    chapter = relationship("Chapter", back_populates="textbook_chunks")


class ContentSource(Base, TimestampMixin):
    """An ingested textbook, exam, answer key, note, or generated source."""

    __tablename__ = "content_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str] = mapped_column(String(50), default="grade_9", nullable=False)
    subject: Mapped[str] = mapped_column(String(80), default="chemistry", nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True, nullable=False)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    chunks = relationship("RagChunk", back_populates="source", cascade="all, delete-orphan")
    extracted_questions = relationship(
        "ExtractedQuestion", back_populates="source", cascade="all, delete-orphan"
    )


class RagChunk(Base, TimestampMixin):
    """General source-grounded vector chunk for textbook and exam retrieval."""

    __tablename__ = "rag_chunks"
    __table_args__ = (
        Index("rag_chunks_source_id_idx", "source_id"),
        Index("rag_chunks_unit_id_idx", "unit_id"),
        Index("rag_chunks_chapter_id_idx", "chapter_id"),
        Index("rag_chunks_lesson_id_idx", "lesson_id"),
        Index("rag_chunks_topic_id_idx", "topic_id"),
        Index("rag_chunks_page_number_idx", "page_number"),
        Index("rag_chunks_content_type_idx", "content_type"),
        Index("rag_chunks_source_type_idx", "source_type"),
        Index(
            "rag_chunks_embedding_idx",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"lists": 100},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("content_sources.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(40), default="text", nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="textbook", nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(80), default="pdf_text", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ar", nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(_embedding_type(), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    embedding_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    embedding_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    source = relationship("ContentSource", back_populates="chunks")
    unit = relationship("Unit", back_populates="rag_chunks")
    chapter = relationship("Chapter", back_populates="rag_chunks")
    lesson = relationship("Lesson", back_populates="rag_chunks")
    topic = relationship("Topic", back_populates="rag_chunks")


class ExtractedQuestion(Base, TimestampMixin):
    """Question extracted from a textbook, exam, answer key, or generated source."""

    __tablename__ = "extracted_questions"
    __table_args__ = (
        Index("extracted_questions_source_id_idx", "source_id"),
        Index("extracted_questions_chapter_id_idx", "chapter_id"),
        Index("extracted_questions_topic_id_idx", "topic_id"),
        Index("extracted_questions_needs_review_idx", "needs_review"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("content_sources.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    options: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_source: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    needs_review: Mapped[bool] = mapped_column(default=True, nullable=False)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    source = relationship("ContentSource", back_populates="extracted_questions")
    chapter = relationship("Chapter")
    lesson = relationship("Lesson")
    topic = relationship("Topic", back_populates="extracted_questions")
