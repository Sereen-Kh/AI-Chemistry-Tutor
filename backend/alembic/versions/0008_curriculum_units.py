"""Add textbook unit hierarchy and lesson-topic links.

Revision ID: 0008_curriculum_units
Revises: 0007_chat_message_rich_metadata
Create Date: 2026-06-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008_curriculum_units"
down_revision = "0007_chat_message_rich_metadata"
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


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if _has_table(table_name) and not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _fk_or_int_column(name: str, target: str) -> sa.Column:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.Column(name, sa.Integer(), nullable=True)
    return sa.Column(name, sa.Integer(), sa.ForeignKey(target, ondelete="SET NULL"), nullable=True)


def upgrade() -> None:
    if not _has_table("units"):
        op.create_table(
            "units",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("unit_number", sa.Integer(), nullable=False),
            sa.Column("semester", sa.Integer(), nullable=False),
            sa.Column("title_ar", sa.String(length=255), nullable=False),
            sa.Column("title_en", sa.String(length=255), nullable=True),
            sa.Column("description_ar", sa.Text(), nullable=True),
            sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("icon", sa.String(length=80), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("unit_number", name="uq_units_unit_number"),
        )
    _create_index_if_missing("ix_units_id", "units", ["id"])
    _create_index_if_missing("ix_units_unit_number", "units", ["unit_number"])
    _create_index_if_missing("ix_units_semester", "units", ["semester"])
    _create_index_if_missing("ix_units_order", "units", ["order"])
    _create_index_if_missing("ix_units_created_at", "units", ["created_at"])

    _add_column_if_missing("chapters", _fk_or_int_column("unit_id", "units.id"))
    _create_index_if_missing("ix_chapters_unit_id", "chapters", ["unit_id"])

    _add_column_if_missing("lessons", sa.Column("page_start", sa.Integer(), nullable=True))
    _add_column_if_missing("lessons", sa.Column("page_end", sa.Integer(), nullable=True))

    if not _has_table("lesson_topics"):
        op.create_table(
            "lesson_topics",
            sa.Column("lesson_id", sa.Integer(), nullable=False),
            sa.Column("topic_id", sa.Integer(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("lesson_id", "topic_id"),
        )
    _create_index_if_missing("ix_lesson_topics_lesson_id", "lesson_topics", ["lesson_id"])
    _create_index_if_missing("ix_lesson_topics_topic_id", "lesson_topics", ["topic_id"])

    _add_column_if_missing("rag_chunks", _fk_or_int_column("unit_id", "units.id"))
    _create_index_if_missing("rag_chunks_unit_id_idx", "rag_chunks", ["unit_id"])


def downgrade() -> None:
    if _has_table("rag_chunks"):
        if _has_index("rag_chunks", "rag_chunks_unit_id_idx"):
            op.drop_index("rag_chunks_unit_id_idx", table_name="rag_chunks")
        if _has_column("rag_chunks", "unit_id"):
            op.drop_column("rag_chunks", "unit_id")

    if _has_table("lesson_topics"):
        if _has_index("lesson_topics", "ix_lesson_topics_topic_id"):
            op.drop_index("ix_lesson_topics_topic_id", table_name="lesson_topics")
        if _has_index("lesson_topics", "ix_lesson_topics_lesson_id"):
            op.drop_index("ix_lesson_topics_lesson_id", table_name="lesson_topics")
        op.drop_table("lesson_topics")

    if _has_table("lessons"):
        if _has_column("lessons", "page_end"):
            op.drop_column("lessons", "page_end")
        if _has_column("lessons", "page_start"):
            op.drop_column("lessons", "page_start")

    if _has_table("chapters"):
        if _has_index("chapters", "ix_chapters_unit_id"):
            op.drop_index("ix_chapters_unit_id", table_name="chapters")
        if _has_column("chapters", "unit_id"):
            op.drop_column("chapters", "unit_id")

    if _has_table("units"):
        for index_name in (
            "ix_units_created_at",
            "ix_units_order",
            "ix_units_semester",
            "ix_units_unit_number",
            "ix_units_id",
        ):
            if _has_index("units", index_name):
                op.drop_index(index_name, table_name="units")
        op.drop_table("units")
