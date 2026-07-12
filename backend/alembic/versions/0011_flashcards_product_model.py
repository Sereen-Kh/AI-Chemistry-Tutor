"""Add deck-based flashcards and spaced repetition metadata.

Revision ID: 0011_flashcards_product_model
Revises: 0010_notifications_push_production
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0011_flashcards_product_model"
down_revision = "0010_notifications_push_production"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if _has_table(table_name) and not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if not _has_table("flashcard_decks"):
        op.create_table(
            "flashcard_decks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("title_ar", sa.String(length=255), nullable=False),
            sa.Column("description_ar", sa.Text(), nullable=False, server_default=""),
            sa.Column("scope_type", sa.String(length=40), nullable=False, server_default="lesson"),
            sa.Column("scope_id", sa.String(length=80), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("source", sa.String(length=40), nullable=False, server_default="book_rag"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing("ix_flashcard_decks_user_id", "flashcard_decks", ["user_id"])
    _create_index_if_missing("ix_flashcard_decks_scope_type", "flashcard_decks", ["scope_type"])
    _create_index_if_missing("ix_flashcard_decks_scope_id", "flashcard_decks", ["scope_id"])
    _create_index_if_missing("ix_flashcard_decks_status", "flashcard_decks", ["status"])

    for column in (
        sa.Column("deck_id", sa.Integer(), sa.ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("card_type", sa.String(length=40), nullable=False, server_default="term_definition"),
        sa.Column("difficulty", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("front_text_ar", sa.Text(), nullable=True),
        sa.Column("back_text_ar", sa.Text(), nullable=True),
        sa.Column("hint_ar", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=False, server_default=""),
        sa.Column("technical_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("explanation_ar", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_page_start", sa.Integer(), nullable=True),
        sa.Column("source_page_end", sa.Integer(), nullable=True),
        sa.Column("source_chunk_ids", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    ):
        _add_column_if_missing("flashcards", column)

    if _has_table("flashcards"):
        op.execute("UPDATE flashcards SET front_text_ar = front_ar WHERE front_text_ar IS NULL")
        op.execute("UPDATE flashcards SET back_text_ar = back_ar WHERE back_text_ar IS NULL")
        op.execute(
            "UPDATE flashcards SET description_ar = 'تختبر هذه البطاقة فهماً كيميائياً من الدرس.' "
            "WHERE description_ar IS NULL OR description_ar = ''"
        )
        op.execute(
            "UPDATE flashcards SET technical_description = 'Legacy flashcard migrated to reviewed flashcard model.' "
            "WHERE technical_description IS NULL OR technical_description = ''"
        )

    for index_name, columns in (
        ("ix_flashcards_deck_id", ["deck_id"]),
        ("ix_flashcards_unit_id", ["unit_id"]),
        ("ix_flashcards_chapter_id", ["chapter_id"]),
        ("ix_flashcards_lesson_id", ["lesson_id"]),
        ("ix_flashcards_card_type", ["card_type"]),
        ("ix_flashcards_difficulty", ["difficulty"]),
    ):
        _create_index_if_missing(index_name, "flashcards", columns)

    for column in (
        sa.Column("status", sa.String(length=30), nullable=False, server_default="new"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ):
        _add_column_if_missing("flashcard_progress", column)

    if _has_table("flashcard_progress"):
        op.execute(
            "UPDATE flashcard_progress SET status = CASE WHEN mastered IS TRUE THEN 'mastered' "
            "WHEN review_count > 0 THEN 'review' ELSE 'new' END WHERE status IS NULL"
        )
        op.execute("UPDATE flashcard_progress SET due_at = next_review_at WHERE due_at IS NULL")
        op.execute("UPDATE flashcard_progress SET last_reviewed_at = last_reviewed WHERE last_reviewed_at IS NULL")
        op.execute("UPDATE flashcard_progress SET repetitions = review_count WHERE repetitions = 0")

    _create_index_if_missing("ix_flashcard_progress_status", "flashcard_progress", ["status"])
    _create_index_if_missing("ix_flashcard_progress_due_at", "flashcard_progress", ["due_at"])


def downgrade() -> None:
    for index_name, table_name in (
        ("ix_flashcard_progress_due_at", "flashcard_progress"),
        ("ix_flashcard_progress_status", "flashcard_progress"),
        ("ix_flashcards_difficulty", "flashcards"),
        ("ix_flashcards_card_type", "flashcards"),
        ("ix_flashcards_lesson_id", "flashcards"),
        ("ix_flashcards_chapter_id", "flashcards"),
        ("ix_flashcards_unit_id", "flashcards"),
        ("ix_flashcards_deck_id", "flashcards"),
    ):
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    for table_name, columns in (
        ("flashcard_progress", ("updated_at", "created_at", "lapses", "repetitions", "last_reviewed_at", "due_at", "status")),
        (
            "flashcards",
            (
                "metadata_json",
                "tags",
                "source_chunk_ids",
                "source_page_end",
                "source_page_start",
                "explanation_ar",
                "technical_description",
                "description_ar",
                "back_text_ar",
                "hint_ar",
                "front_text_ar",
                "difficulty",
                "card_type",
                "lesson_id",
                "chapter_id",
                "unit_id",
                "deck_id",
            ),
        ),
    ):
        if not _has_table(table_name):
            continue
        for column_name in columns:
            if _has_column(table_name, column_name):
                op.drop_column(table_name, column_name)

    if _has_table("flashcard_decks"):
        op.drop_table("flashcard_decks")
