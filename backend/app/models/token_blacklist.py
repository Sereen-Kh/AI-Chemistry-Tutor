from datetime import datetime

from sqlalchemy import (
    String,
    DateTime
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.db.base import Base


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    token: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )