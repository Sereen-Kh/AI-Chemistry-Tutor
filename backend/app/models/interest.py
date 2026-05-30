"""Interest category models for personalization."""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base


class InterestCategory(Base):
    """Selectable student interest used for personalized examples."""

    __tablename__ = "interest_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    users = relationship("UserInterest", back_populates="interest", cascade="all, delete-orphan")


class UserInterest(Base):
    """Many-to-many link between users and interest categories."""

    __tablename__ = "user_interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    interest_id: Mapped[int] = mapped_column(
        ForeignKey("interest_categories.id", ondelete="CASCADE"), index=True
    )
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="interests")
    interest = relationship("InterestCategory", back_populates="users")
