"""Interactive problem-solving lab models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class InteractiveSession(Base, TimestampMixin):
    """A guided step-by-step chemistry problem-solving session."""

    __tablename__ = "interactive_sessions"
    __table_args__ = (
        Index("interactive_sessions_user_status_idx", "user_id", "status"),
        Index("interactive_sessions_problem_type_idx", "problem_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    problem_text: Mapped[str] = mapped_column(Text, nullable=False)
    problem_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_chunks: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    weak_topics: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="interactive_sessions")
    steps = relationship(
        "InteractiveStep",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InteractiveStep.step_index.asc()",
    )
    answers = relationship("StudentStepAnswer", back_populates="session", cascade="all, delete-orphan")
    misconceptions = relationship("MisconceptionEvent", back_populates="session", cascade="all, delete-orphan")


class InteractiveStep(Base, TimestampMixin):
    """One expected student action inside an interactive session."""

    __tablename__ = "interactive_steps"
    __table_args__ = (
        Index("interactive_steps_session_index_idx", "session_id", "step_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interactive_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_ar: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer_type: Mapped[str] = mapped_column(String(30), nullable=False)
    expected_formula: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tolerance: Mapped[float] = mapped_column(Float, default=0.02, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    hint_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    session = relationship("InteractiveSession", back_populates="steps")
    answers = relationship("StudentStepAnswer", back_populates="step", cascade="all, delete-orphan")


class StudentStepAnswer(Base, TimestampMixin):
    """A student's submitted answer for one interactive step."""

    __tablename__ = "student_step_answers"
    __table_args__ = (
        Index("student_step_answers_session_created_idx", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interactive_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[int] = mapped_column(ForeignKey("interactive_steps.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    feedback_ar: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    parsed_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    misconception_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    session = relationship("InteractiveSession", back_populates="answers")
    step = relationship("InteractiveStep", back_populates="answers")
    user = relationship("User", back_populates="interactive_step_answers")


class MisconceptionEvent(Base, TimestampMixin):
    """Detected misconception for later weak-topic analytics."""

    __tablename__ = "misconception_events"
    __table_args__ = (
        Index("misconception_events_user_type_idx", "user_id", "misconception_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interactive_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[int | None] = mapped_column(ForeignKey("interactive_steps.id", ondelete="SET NULL"), nullable=True)
    misconception_type: Mapped[str] = mapped_column(String(80), nullable=False)
    topic_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description_ar: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="misconception_events")
    session = relationship("InteractiveSession", back_populates="misconceptions")


class SkillMastery(Base, TimestampMixin):
    """Aggregated mastery estimate for an interactive solving skill."""

    __tablename__ = "skill_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_key", name="uq_skill_mastery_user_skill"),
        Index("skill_mastery_user_skill_idx", "user_id", "skill_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_key: Mapped[str] = mapped_column(String(120), nullable=False)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="skill_mastery")
