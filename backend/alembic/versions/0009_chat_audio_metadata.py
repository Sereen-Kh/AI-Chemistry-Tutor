"""Add chat audio modality metadata.

Revision ID: 0009_chat_audio_metadata
Revises: 0008_curriculum_units
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009_chat_audio_metadata"
down_revision = "0008_curriculum_units"
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


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    if not _has_table("chat_messages"):
        return

    _add_column_if_missing("chat_messages", sa.Column("input_type", sa.String(length=20), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("requested_return_type", sa.String(length=20), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("resolved_return_type", sa.String(length=20), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("text_content", sa.Text(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("audio_input_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("audio_transcript", sa.Text(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("answer_text", sa.Text(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("answer_audio_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("transcription_status", sa.String(length=30), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("audio_status", sa.String(length=30), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("audio_provider", sa.String(length=50), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("tts_model", sa.String(length=100), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("stt_model", sa.String(length=100), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("voice_id", sa.String(length=120), nullable=True))


def downgrade() -> None:
    if not _has_table("chat_messages"):
        return

    for column_name in (
        "voice_id",
        "stt_model",
        "tts_model",
        "audio_provider",
        "audio_status",
        "transcription_status",
        "answer_audio_url",
        "answer_text",
        "audio_transcript",
        "audio_input_url",
        "text_content",
        "resolved_return_type",
        "requested_return_type",
        "input_type",
    ):
        if _has_column("chat_messages", column_name):
            op.drop_column("chat_messages", column_name)
