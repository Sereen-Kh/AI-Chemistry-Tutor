"""Add RAG embedding status columns.

Revision ID: 0006_rag_embedding_status
Revises: 0005_interactive_solver
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_rag_embedding_status"
down_revision = "0005_interactive_solver"
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


def upgrade() -> None:
    if not _has_table("rag_chunks"):
        return

    if not _has_column("rag_chunks", "embedding_status"):
        op.add_column(
            "rag_chunks",
            sa.Column("embedding_status", sa.String(length=40), nullable=False, server_default="pending"),
        )
    if not _has_column("rag_chunks", "embedding_error"):
        op.add_column("rag_chunks", sa.Column("embedding_error", sa.Text(), nullable=True))
    if not _has_index("rag_chunks", "ix_rag_chunks_embedding_status"):
        op.create_index("ix_rag_chunks_embedding_status", "rag_chunks", ["embedding_status"])


def downgrade() -> None:
    if not _has_table("rag_chunks"):
        return

    if _has_index("rag_chunks", "ix_rag_chunks_embedding_status"):
        op.drop_index("ix_rag_chunks_embedding_status", table_name="rag_chunks")
    if _has_column("rag_chunks", "embedding_error"):
        op.drop_column("rag_chunks", "embedding_error")
    if _has_column("rag_chunks", "embedding_status"):
        op.drop_column("rag_chunks", "embedding_status")
