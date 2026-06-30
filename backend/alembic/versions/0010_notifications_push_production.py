"""Expand notifications and push tokens for production reminders.

Revision ID: 0010_notifications_push_production
Revises: 0009_chat_audio_metadata
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0010_notifications_push_production"
down_revision = "0009_chat_audio_metadata"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table_name):
        return False
    return any(column["name"] == column_name for column in sa.inspect(bind).get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table_name):
        return False
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing("notifications", sa.Column("title_ar", sa.String(length=255), nullable=True))
    _add_column_if_missing("notifications", sa.Column("body_ar", sa.Text(), nullable=True))
    _add_column_if_missing("notifications", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("notifications", sa.Column("related_entity_type", sa.String(length=50), nullable=True))
    _add_column_if_missing("notifications", sa.Column("related_entity_id", sa.String(length=80), nullable=True))
    if _has_table("notifications"):
        op.execute("UPDATE notifications SET title_ar = title WHERE title_ar IS NULL")
        op.execute("UPDATE notifications SET body_ar = message WHERE body_ar IS NULL")
        if not _has_index("notifications", "ix_notifications_user_type_scheduled"):
            op.create_index(
                "ix_notifications_user_type_scheduled",
                "notifications",
                ["user_id", "type", "scheduled_for"],
            )

    for column in (
        sa.Column("daily_study_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("daily_study_reminder_time", sa.String(length=10), nullable=False, server_default="08:00"),
        sa.Column("exam_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("flashcards_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("overdue_lesson_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weak_topic_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quiet_hours_start", sa.String(length=10), nullable=False, server_default="22:00"),
        sa.Column("quiet_hours_end", sa.String(length=10), nullable=False, server_default="07:00"),
    ):
        _add_column_if_missing("notification_preferences", column)
    if _has_table("notification_preferences"):
        op.execute(
            "UPDATE notification_preferences "
            "SET daily_study_reminder_time = reminder_time_local "
            "WHERE daily_study_reminder_time IS NULL"
        )

    for column in (
        sa.Column("device_name", sa.String(length=120), nullable=True),
        sa.Column("browser", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    ):
        _add_column_if_missing("device_tokens", column)
    if _has_table("device_tokens") and not _has_index("device_tokens", "ix_device_tokens_user_active"):
        op.create_index("ix_device_tokens_user_active", "device_tokens", ["user_id", "is_active"])


def downgrade() -> None:
    for index_name, table_name in (
        ("ix_device_tokens_user_active", "device_tokens"),
        ("ix_notifications_user_type_scheduled", "notifications"),
    ):
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    for table_name, columns in (
        ("device_tokens", ("last_seen_at", "is_active", "browser", "device_name")),
        (
            "notification_preferences",
            (
                "quiet_hours_end",
                "quiet_hours_start",
                "quiet_hours_enabled",
                "weak_topic_reminder_enabled",
                "overdue_lesson_reminder_enabled",
                "flashcards_reminder_enabled",
                "exam_reminder_enabled",
                "daily_study_reminder_time",
                "daily_study_reminder_enabled",
            ),
        ),
        ("notifications", ("related_entity_id", "related_entity_type", "sent_at", "body_ar", "title_ar")),
    ):
        if not _has_table(table_name):
            continue
        for column_name in columns:
            if _has_column(table_name, column_name):
                op.drop_column(table_name, column_name)
