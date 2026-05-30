"""Homework problem-solving model."""

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Homework(Base, TimestampMixin):
    """Student homework submission and AI-produced solution."""

    __tablename__ = "homework"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    problem_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_chunks: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    user = relationship("User", back_populates="homework_items")
    topic = relationship("Topic", back_populates="homework_items")
