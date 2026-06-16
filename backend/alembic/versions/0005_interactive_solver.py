"""Add guided interactive chemistry solver tables.

Revision ID: 0005_interactive_solver
Revises: 0004_rag_hardening
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_interactive_solver"
down_revision = "0004_rag_hardening"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table_name):
        return False
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _create_index_once(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if not _has_table("interactive_sessions"):
        op.create_table(
            "interactive_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("topic_id", sa.Integer(), nullable=True),
            sa.Column("problem_text", sa.Text(), nullable=False),
            sa.Column("problem_type", sa.String(length=80), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("current_step_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_chunks", sa.JSON(), nullable=True),
            sa.Column("final_answer", sa.Text(), nullable=True),
            sa.Column("summary_json", sa.JSON(), nullable=True),
            sa.Column("weak_topics", sa.JSON(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_interactive_sessions_id", "interactive_sessions", ["id"])
        op.create_index("ix_interactive_sessions_user_id", "interactive_sessions", ["user_id"])
    _create_index_once("interactive_sessions_user_status_idx", "interactive_sessions", ["user_id", "status"])
    _create_index_once("interactive_sessions_problem_type_idx", "interactive_sessions", ["problem_type"])

    if not _has_table("interactive_steps"):
        op.create_table(
            "interactive_steps",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("step_index", sa.Integer(), nullable=False),
            sa.Column("step_key", sa.String(length=80), nullable=False),
            sa.Column("title_ar", sa.String(length=255), nullable=False),
            sa.Column("prompt_ar", sa.Text(), nullable=False),
            sa.Column("expected_answer_type", sa.String(length=30), nullable=False),
            sa.Column("expected_formula", sa.String(length=255), nullable=True),
            sa.Column("expected_numeric", sa.Float(), nullable=True),
            sa.Column("expected_unit", sa.String(length=40), nullable=True),
            sa.Column("tolerance", sa.Float(), nullable=False, server_default="0.02"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("hint_ar", sa.Text(), nullable=True),
            sa.Column("explanation_ar", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["interactive_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_interactive_steps_id", "interactive_steps", ["id"])
        op.create_index("ix_interactive_steps_session_id", "interactive_steps", ["session_id"])
    _create_index_once("interactive_steps_session_index_idx", "interactive_steps", ["session_id", "step_index"])

    if not _has_table("student_step_answers"):
        op.create_table(
            "student_step_answers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("step_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("answer_text", sa.Text(), nullable=False),
            sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("feedback_ar", sa.Text(), nullable=False),
            sa.Column("parsed_value", sa.Float(), nullable=True),
            sa.Column("parsed_unit", sa.String(length=40), nullable=True),
            sa.Column("misconception_type", sa.String(length=80), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["interactive_sessions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["step_id"], ["interactive_steps.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_student_step_answers_id", "student_step_answers", ["id"])
        op.create_index("ix_student_step_answers_user_id", "student_step_answers", ["user_id"])
        op.create_index("ix_student_step_answers_session_id", "student_step_answers", ["session_id"])
    _create_index_once("student_step_answers_session_created_idx", "student_step_answers", ["session_id", "created_at"])

    if not _has_table("misconception_events"):
        op.create_table(
            "misconception_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("step_id", sa.Integer(), nullable=True),
            sa.Column("misconception_type", sa.String(length=80), nullable=False),
            sa.Column("topic_key", sa.String(length=120), nullable=True),
            sa.Column("description_ar", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["interactive_sessions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["step_id"], ["interactive_steps.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_misconception_events_id", "misconception_events", ["id"])
        op.create_index("ix_misconception_events_user_id", "misconception_events", ["user_id"])
    _create_index_once("misconception_events_user_type_idx", "misconception_events", ["user_id", "misconception_type"])

    if not _has_table("skill_mastery"):
        op.create_table(
            "skill_mastery",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("skill_key", sa.String(length=120), nullable=False),
            sa.Column("mastery_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("correct_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "skill_key", name="uq_skill_mastery_user_skill"),
        )
        op.create_index("ix_skill_mastery_id", "skill_mastery", ["id"])
        op.create_index("ix_skill_mastery_user_id", "skill_mastery", ["user_id"])
    _create_index_once("skill_mastery_user_skill_idx", "skill_mastery", ["user_id", "skill_key"])


def downgrade() -> None:
    for table_name in (
        "skill_mastery",
        "misconception_events",
        "student_step_answers",
        "interactive_steps",
        "interactive_sessions",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)
