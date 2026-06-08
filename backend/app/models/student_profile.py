import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    ForeignKey,
    String
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.db.base import Base
from app.core.constants import (
    PreferredLanguage
)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True
    )

    grade: Mapped[int] = mapped_column(
        Integer,
        default=9
    )

    preferred_language: Mapped[str] = mapped_column(
        String(10),
        default=PreferredLanguage.ARABIC.value
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    onboarding_completed: Mapped[bool] = mapped_column(
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="student_profile"
    )