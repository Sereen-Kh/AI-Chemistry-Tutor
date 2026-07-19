"""Chat session and message models."""

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class ChatSession(Base, TimestampMixin):
    """Container for a tutoring conversation."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    style: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base, TimestampMixin):
    """One user or assistant message in a chat session."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="text", nullable=False)
    feedback: Mapped[str | None] = mapped_column(String(30), nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    route: Mapped[str | None] = mapped_column(String(80), nullable=True)
    grounding: Mapped[str | None] = mapped_column(String(80), nullable=True)
    input_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    requested_return_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_return_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_input_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcription_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    audio_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    audio_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tts_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stt_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    voice_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sources_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    citations_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    external_sources_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    blocks_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    media_blocks_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    source_blocks_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    page_numbers_json: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    diagnostics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    suggested_next_action: Mapped[str | None] = mapped_column(String(255), nullable=True)

    session = relationship("ChatSession", back_populates="messages")

    @property
    def sources(self) -> list[dict[str, Any]]:
        return self.sources_json or []

    @property
    def citations(self) -> list[dict[str, Any]]:
        return self.citations_json or []

    @property
    def external_sources(self) -> list[dict[str, Any]]:
        return self.external_sources_json or []

    @property
    def blocks(self) -> list[dict[str, Any]]:
        return self.blocks_json or []

    @property
    def media_blocks(self) -> list[dict[str, Any]]:
        return self.media_blocks_json or []

    @property
    def source_blocks(self) -> list[dict[str, Any]]:
        return self.source_blocks_json or []

    @property
    def page_numbers(self) -> list[int]:
        return self.page_numbers_json or []

    @property
    def diagnostics(self) -> dict[str, Any]:
        return self.diagnostics_json or {}

    @property
    def display_answer_text(self) -> str:
        return self.answer_text or self.content
