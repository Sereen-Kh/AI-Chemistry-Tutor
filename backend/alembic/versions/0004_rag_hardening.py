"""Add RAG embedding metadata and retrieval logs.

Revision ID: 0004_rag_hardening
Revises: 0003_notifications
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_rag_hardening"
down_revision = "0003_notifications"
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


def _create_index_once(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if _has_table("rag_chunks"):
        if not _has_column("rag_chunks", "embedding_model"):
            op.add_column("rag_chunks", sa.Column("embedding_model", sa.String(length=120), nullable=True))
        if not _has_column("rag_chunks", "embedding_updated_at"):
            op.add_column("rag_chunks", sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True))
        _create_index_once("ix_rag_chunks_embedding_model", "rag_chunks", ["embedding_model"])

    if not _has_table("rag_query_logs"):
        op.create_table(
            "rag_query_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column("normalized_query", sa.Text(), nullable=True),
            sa.Column("route", sa.String(length=80), nullable=False),
            sa.Column("source_mode", sa.String(length=80), nullable=True),
            sa.Column("top_k", sa.Integer(), nullable=False),
            sa.Column("min_similarity", sa.Float(), nullable=False, server_default="0"),
            sa.Column("embedding_model", sa.String(length=120), nullable=True),
            sa.Column("retrieval_latency_ms", sa.Integer(), nullable=True),
            sa.Column("generation_latency_ms", sa.Integer(), nullable=True),
            sa.Column("total_latency_ms", sa.Integer(), nullable=True),
            sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_similarity", sa.Float(), nullable=True),
            sa.Column("avg_similarity", sa.Float(), nullable=True),
            sa.Column("low_confidence", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("answer_confidence", sa.Float(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_rag_query_logs_id", "rag_query_logs", ["id"])
        op.create_index("ix_rag_query_logs_user_id", "rag_query_logs", ["user_id"])
        op.create_index("ix_rag_query_logs_created_at", "rag_query_logs", ["created_at"])

    _create_index_once("rag_query_logs_user_created_idx", "rag_query_logs", ["user_id", "created_at"])
    _create_index_once("rag_query_logs_route_created_idx", "rag_query_logs", ["route", "created_at"])
    _create_index_once("rag_query_logs_low_confidence_idx", "rag_query_logs", ["low_confidence"])

    if not _has_table("retrieved_chunk_logs"):
        op.create_table(
            "retrieved_chunk_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("rag_query_log_id", sa.Integer(), nullable=False),
            sa.Column("chunk_id", sa.Integer(), nullable=True),
            sa.Column("source_id", sa.Integer(), nullable=True),
            sa.Column("source_type", sa.String(length=40), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("content_type", sa.String(length=40), nullable=True),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("similarity_score", sa.Float(), nullable=True),
            sa.Column("hybrid_score", sa.Float(), nullable=True),
            sa.Column("rerank_score", sa.Float(), nullable=True),
            sa.Column("used_in_answer", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["chunk_id"], ["rag_chunks.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["rag_query_log_id"], ["rag_query_logs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_retrieved_chunk_logs_id", "retrieved_chunk_logs", ["id"])
        op.create_index("ix_retrieved_chunk_logs_rag_query_log_id", "retrieved_chunk_logs", ["rag_query_log_id"])

    _create_index_once("retrieved_chunk_logs_query_rank_idx", "retrieved_chunk_logs", ["rag_query_log_id", "rank"])
    _create_index_once("retrieved_chunk_logs_chunk_idx", "retrieved_chunk_logs", ["chunk_id"])
    _create_index_once("retrieved_chunk_logs_source_type_idx", "retrieved_chunk_logs", ["source_type"])


def downgrade() -> None:
    if _has_table("retrieved_chunk_logs"):
        op.drop_table("retrieved_chunk_logs")
    if _has_table("rag_query_logs"):
        op.drop_table("rag_query_logs")
    if _has_table("rag_chunks"):
        if _has_column("rag_chunks", "embedding_updated_at"):
            op.drop_column("rag_chunks", "embedding_updated_at")
        if _has_column("rag_chunks", "embedding_model"):
            op.drop_column("rag_chunks", "embedding_model")
