"""Persistent RAG retrieval observability models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class RagQueryLog(Base):
    """One retrieval/generation query issued by a user or admin tool."""

    __tablename__ = "rag_query_logs"
    __table_args__ = (
        Index("rag_query_logs_user_created_idx", "user_id", "created_at"),
        Index("rag_query_logs_route_created_idx", "route", "created_at"),
        Index("rag_query_logs_low_confidence_idx", "low_confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    route: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_mode: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    min_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    retrieval_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answer_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    retrieved_chunks = relationship(
        "RetrievedChunkLog",
        back_populates="rag_query_log",
        cascade="all, delete-orphan",
        order_by="RetrievedChunkLog.rank.asc()",
    )


class RetrievedChunkLog(Base):
    """A chunk returned for a RAG query, with ranking and scoring metadata."""

    __tablename__ = "retrieved_chunk_logs"
    __table_args__ = (
        Index("retrieved_chunk_logs_query_rank_idx", "rag_query_log_id", "rank"),
        Index("retrieved_chunk_logs_chunk_idx", "chunk_id"),
        Index("retrieved_chunk_logs_source_type_idx", "source_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rag_query_log_id: Mapped[int] = mapped_column(
        ForeignKey("rag_query_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("rag_chunks.id", ondelete="SET NULL"), nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hybrid_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    used_in_answer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    rag_query_log = relationship("RagQueryLog", back_populates="retrieved_chunks")
