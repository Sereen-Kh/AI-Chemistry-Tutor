"""Add rich chat message metadata columns.

Revision ID: 0007_chat_message_rich_metadata
Revises: 0006_rag_embedding_status
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_chat_message_rich_metadata"
down_revision = "0006_rag_embedding_status"
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

    _add_column_if_missing("chat_messages", sa.Column("confidence", sa.Float(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("answer_type", sa.String(length=50), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("route", sa.String(length=80), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("grounding", sa.String(length=80), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("sources_json", sa.JSON(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("citations_json", sa.JSON(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("blocks_json", sa.JSON(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("media_blocks_json", sa.JSON(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("source_blocks_json", sa.JSON(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("page_numbers_json", sa.JSON(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("diagnostics_json", sa.JSON(), nullable=True))
    _add_column_if_missing("chat_messages", sa.Column("suggested_next_action", sa.String(length=255), nullable=True))


def downgrade() -> None:
    if not _has_table("chat_messages"):
        return

    for column_name in (
        "suggested_next_action",
        "diagnostics_json",
        "page_numbers_json",
        "source_blocks_json",
        "media_blocks_json",
        "blocks_json",
        "citations_json",
        "sources_json",
        "grounding",
        "route",
        "answer_type",
        "confidence",
    ):
        if _has_column("chat_messages", column_name):
            op.drop_column("chat_messages", column_name)
