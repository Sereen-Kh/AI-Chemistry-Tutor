from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class StudentAttempt(Base):
    __tablename__ = "student_attempts"

    id = Column(String, primary_key=True)

    user_id = Column(
        String,
        ForeignKey("users.id")
    )

    user = relationship(
        "User",
        back_populates="student_attempts"
    )