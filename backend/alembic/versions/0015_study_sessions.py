"""Add persistent Study Session lifecycle.

Revision ID: 0015_study_sessions
Revises: 0014_ask_ai_memory_web_grounding
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_study_sessions"
down_revision = "0014_ask_ai_memory_web_grounding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("study_plan_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="running"),
        sa.Column("planned_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'paused', 'completed', 'abandoned')",
            name="ck_study_sessions_status",
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["study_plan_id"], ["study_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_sessions_id", "study_sessions", ["id"])
    op.create_index("ix_study_sessions_user_id", "study_sessions", ["user_id"])
    op.create_index("ix_study_sessions_lesson_id", "study_sessions", ["lesson_id"])
    op.create_index("ix_study_sessions_study_plan_id", "study_sessions", ["study_plan_id"])
    op.create_index("ix_study_sessions_status", "study_sessions", ["status"])
    op.create_index("study_sessions_user_status_idx", "study_sessions", ["user_id", "status"])
    op.create_index(
        "study_sessions_user_lesson_created_idx",
        "study_sessions",
        ["user_id", "lesson_id", "created_at"],
    )
    op.create_index(
        "uq_study_sessions_user_lesson_open",
        "study_sessions",
        ["user_id", "lesson_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('running', 'paused')"),
        sqlite_where=sa.text("status IN ('running', 'paused')"),
    )
    op.create_index(
        "uq_study_sessions_user_running",
        "study_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("uq_study_sessions_user_running", table_name="study_sessions")
    op.drop_index("uq_study_sessions_user_lesson_open", table_name="study_sessions")
    op.drop_index("study_sessions_user_lesson_created_idx", table_name="study_sessions")
    op.drop_index("study_sessions_user_status_idx", table_name="study_sessions")
    op.drop_index("ix_study_sessions_status", table_name="study_sessions")
    op.drop_index("ix_study_sessions_study_plan_id", table_name="study_sessions")
    op.drop_index("ix_study_sessions_lesson_id", table_name="study_sessions")
    op.drop_index("ix_study_sessions_user_id", table_name="study_sessions")
    op.drop_index("ix_study_sessions_id", table_name="study_sessions")
    op.drop_table("study_sessions")
