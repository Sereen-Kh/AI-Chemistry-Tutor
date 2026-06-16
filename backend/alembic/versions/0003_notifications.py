"""Add reminder notification system.

Revision ID: 0003_notifications
Revises: 0002_preference_dimensions
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_notifications"
down_revision = "0002_preference_dimensions"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    return any(
        constraint["name"] == constraint_name
        for constraint in sa.inspect(bind).get_unique_constraints(table_name)
    )


def upgrade() -> None:
    if not _has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="unread"),
            sa.Column("priority", sa.String(length=30), nullable=False, server_default="normal"),
            sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("action_url", sa.String(length=255), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notifications_id", "notifications", ["id"])
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    if not _has_index("notifications", "ix_notifications_user_status_scheduled"):
        op.create_index(
            "ix_notifications_user_status_scheduled",
            "notifications",
            ["user_id", "status", "scheduled_for"],
        )

    if not _has_table("notification_preferences"):
        op.create_table(
            "notification_preferences",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("exam_reminders_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("lesson_reminders_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("reminder_time_local", sa.String(length=10), nullable=False, server_default="08:00"),
            sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
        )
        op.create_index("ix_notification_preferences_id", "notification_preferences", ["id"])
        op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])

    if not _has_table("reminder_events"):
        op.create_table(
            "reminder_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("source_type", sa.String(length=30), nullable=False),
            sa.Column("source_id", sa.String(length=50), nullable=False),
            sa.Column("reminder_type", sa.String(length=50), nullable=False),
            sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("notification_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "source_type",
                "source_id",
                "reminder_type",
                name="uq_reminder_event_user_source_type",
            ),
        )
        op.create_index("ix_reminder_events_id", "reminder_events", ["id"])
        op.create_index("ix_reminder_events_user_id", "reminder_events", ["user_id"])
    elif op.get_bind().dialect.name != "sqlite" and not _has_unique_constraint(
        "reminder_events", "uq_reminder_event_user_source_type"
    ):
        op.create_unique_constraint(
            "uq_reminder_event_user_source_type",
            "reminder_events",
            ["user_id", "source_type", "source_id", "reminder_type"],
        )

    if not _has_index("reminder_events", "ix_reminder_events_status_scheduled"):
        op.create_index(
            "ix_reminder_events_status_scheduled",
            "reminder_events",
            ["status", "scheduled_for"],
        )


def downgrade() -> None:
    for table_name in ("reminder_events", "notification_preferences", "notifications"):
        if _has_table(table_name):
            op.drop_table(table_name)
