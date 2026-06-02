"""Persistent ingestion job and page state."""

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class IngestionJob(Base, TimestampMixin):
    """One admin-started ingestion run."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    errors_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    source = relationship("ContentSource")


class IngestionPage(Base, TimestampMixin):
    """Per-page ingestion status and cache location."""

    __tablename__ = "ingestion_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("content_sources.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_jobs.id", ondelete="SET NULL"), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    page_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True, nullable=False)
    extraction_methods: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    cache_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    warnings_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    errors_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)

    source = relationship("ContentSource")
    job = relationship("IngestionJob")
