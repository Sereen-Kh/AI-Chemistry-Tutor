from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class GeneratedQuestion(Base):
    __tablename__ = "generated_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    lesson: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    question_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    difficulty: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
    )

    options: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    answer: Mapped[str] = mapped_column(
        Text,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )