import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.db.base import Base
from app.core.constants import UserRole, SubscriptionStatus, Gender

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    full_name: Mapped[str] = mapped_column(
        String(255)
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    gender: Mapped[str] = mapped_column(
        String(30),
        default=Gender.PREFER_NOT_TO_SAY.value
    )

    hashed_password: Mapped[str] = mapped_column(
        String
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.STUDENT.value
    )

    subscription_status: Mapped[str] = mapped_column(
        String(50),
        default=SubscriptionStatus.FREE.value
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
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

    student_profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    learning_preference = relationship(
        "LearningPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    password_reset_tokens = relationship(
        "PasswordResetToken",
        cascade="all, delete-orphan"
    )

    conversations = relationship(
        "Conversation",
        backref="user",
        cascade="all, delete-orphan"
    )

    student_attempts = relationship(
        "StudentAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
    )