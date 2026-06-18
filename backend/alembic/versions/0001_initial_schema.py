"""Initial EduMind schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-31

This migration intentionally does not call ``Base.metadata.create_all()``.
It is a frozen baseline for the schema before revisions 0002-0008. Later
revisions own preference dimensions, notifications, RAG logging, interactive
solver tables, embedding status, rich chat metadata, and curriculum units.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table_name):
        return False
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: Sequence[str],
    **kwargs,
) -> None:
    if _has_table(table_name) and not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, list(columns), **kwargs)


def _create_table_if_missing(table_name: str, *elements) -> None:
    if not _has_table(table_name):
        op.create_table(table_name, *elements)


def _ts_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def _json_type() -> sa.JSON:
    return sa.JSON()


def _embedding_type():
    if op.get_bind().dialect.name == "postgresql":
        from pgvector.sqlalchemy import Vector

        return Vector(768)
    return sa.JSON()


def _create_pgvector_extension() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def _create_core_tables() -> None:
    _create_table_if_missing(
        "content_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("grade", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=True),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "elements",
        sa.Column("atomic_number", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=4), nullable=False),
        sa.Column("name_ar", sa.String(length=80), nullable=False),
        sa.Column("name_en", sa.String(length=80), nullable=False),
        sa.Column("atomic_mass", sa.Float(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("period", sa.Integer(), nullable=True),
        sa.Column("group", sa.Integer(), nullable=True),
        sa.Column("electron_configuration", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("atomic_number"),
        sa.UniqueConstraint("symbol"),
    )

    _create_table_if_missing(
        "interest_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name_ar", sa.String(length=120), nullable=False),
        sa.Column("name_en", sa.String(length=120), nullable=True),
        sa.Column("icon", sa.String(length=40), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    _create_table_if_missing(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title_ar", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("icon", sa.String(length=80), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("grade", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=50), nullable=False),
        sa.Column("teaching_style", sa.String(length=50), nullable=False),
        sa.Column("answer_format", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("streak_days", sa.Integer(), nullable=False),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    _create_table_if_missing(
        "chapters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title_ar", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("icon", sa.String(length=80), nullable=True),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=True),
        sa.Column("icon", sa.String(length=80), nullable=True),
        sa.Column("condition", sa.String(length=255), nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    _create_table_if_missing(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("title_ar", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=True),
        sa.Column("content_ar", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=80), nullable=False),
        sa.Column("learning_style", sa.String(length=80), nullable=False),
        sa.Column("preferred_language", sa.String(length=8), nullable=False),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("target_exam_date", sa.Date(), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    _create_table_if_missing(
        "user_interests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("interest_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["interest_id"], ["interest_categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("plan", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("trial_messages_used", sa.Integer(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    _create_table_if_missing(
        "study_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("plan_json", _json_type(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_learning_tables() -> None:
    _create_table_if_missing(
        "flashcards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("front_ar", sa.Text(), nullable=False),
        sa.Column("back_ar", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=30), nullable=False),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("question_ar", sa.Text(), nullable=False),
        sa.Column("options", _json_type(), nullable=False),
        sa.Column("correct_answer", sa.Integer(), nullable=False),
        sa.Column("explanation_ar", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("answers", _json_type(), nullable=True),
        sa.Column("weak_topics", _json_type(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "user_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("flashcards_mastered", sa.Integer(), nullable=False),
        sa.Column("quizzes_completed", sa.Integer(), nullable=False),
        sa.Column("best_quiz_score", sa.Float(), nullable=False),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "flashcard_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("flashcard_id", sa.Integer(), nullable=False),
        sa.Column("mastered", sa.Boolean(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("ease_factor", sa.Float(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("next_review_at", sa.Date(), nullable=True),
        sa.Column("last_reviewed", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["flashcard_id"], ["flashcards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "lesson_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "homework",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("problem_text", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("solution", sa.Text(), nullable=False),
        sa.Column("source_chunks", _json_type(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_content_tables() -> None:
    _create_table_if_missing(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_uid", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("result_json", _json_type(), nullable=True),
        sa.Column("errors_json", _json_type(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_uid"),
    )

    _create_table_if_missing(
        "ingestion_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("page_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("extraction_methods", _json_type(), nullable=True),
        sa.Column("cache_path", sa.String(length=500), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("completeness_score", sa.Float(), nullable=False),
        sa.Column("warnings_json", _json_type(), nullable=True),
        sa.Column("errors_json", _json_type(), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "textbook_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=True),
        sa.Column("extraction_method", sa.String(length=80), nullable=True),
        sa.Column("embedding", _embedding_type(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "rag_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("embedding", _embedding_type(), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "extracted_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=40), nullable=False),
        sa.Column("options", _json_type(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("answer_source", sa.String(length=40), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_chat_and_media_tables() -> None:
    _create_table_if_missing(
        "chat_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("style", sa.String(length=50), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "reels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("audio_url", sa.String(length=500), nullable=True),
        sa.Column("script", sa.Text(), nullable=False),
        sa.Column("visual_cues", _json_type(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id"),
    )

    _create_table_if_missing(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("feedback", sa.String(length=30), nullable=True),
        sa.Column("media_url", sa.String(length=500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        *_ts_columns(),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        "question_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("selected_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("weak_topics", _json_type(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["extracted_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_indexes() -> None:
    for table_name, columns in {
        "achievements": ("id", "user_id"),
        "chapters": ("id", "order", "created_at"),
        "chat_messages": ("id", "session_id", "created_at"),
        "chat_sessions": ("id", "user_id", "lesson_id", "created_at"),
        "content_sources": ("id", "source_type", "status", "year", "created_at"),
        "device_tokens": ("id", "user_id", "created_at"),
        "elements": ("symbol",),
        "flashcard_progress": ("id", "user_id", "flashcard_id"),
        "flashcards": ("id", "topic_id", "created_at"),
        "homework": ("id", "user_id", "topic_id", "created_at"),
        "ingestion_jobs": ("id", "job_uid", "source_id", "status", "created_at"),
        "ingestion_pages": ("id", "source_id", "page_number", "status", "created_at"),
        "interest_categories": ("id", "key"),
        "lesson_progress": ("id", "user_id", "lesson_id"),
        "lessons": ("id", "chapter_id", "order", "created_at"),
        "questions": ("id", "topic_id", "created_at"),
        "quiz_attempts": ("id", "user_id", "topic_id"),
        "reels": ("id", "lesson_id"),
        "student_profiles": ("id", "user_id", "created_at"),
        "study_plans": ("id", "user_id", "created_at"),
        "subscriptions": ("id", "user_id", "created_at"),
        "textbook_chunks": ("id", "chapter_id", "page_number", "created_at"),
        "topics": ("id", "order", "created_at"),
        "user_interests": ("id", "user_id", "interest_id"),
        "user_progress": ("id", "user_id", "topic_id"),
        "users": ("id", "email", "created_at"),
    }.items():
        for column in columns:
            _create_index_if_missing(f"ix_{table_name}_{column}", table_name, [column])

    _create_index_if_missing("rag_chunks_source_id_idx", "rag_chunks", ["source_id"])
    _create_index_if_missing("rag_chunks_chapter_id_idx", "rag_chunks", ["chapter_id"])
    _create_index_if_missing("rag_chunks_lesson_id_idx", "rag_chunks", ["lesson_id"])
    _create_index_if_missing("rag_chunks_topic_id_idx", "rag_chunks", ["topic_id"])
    _create_index_if_missing("rag_chunks_page_number_idx", "rag_chunks", ["page_number"])
    _create_index_if_missing("rag_chunks_content_type_idx", "rag_chunks", ["content_type"])
    _create_index_if_missing("rag_chunks_source_type_idx", "rag_chunks", ["source_type"])
    _create_index_if_missing("ix_rag_chunks_id", "rag_chunks", ["id"])
    _create_index_if_missing("ix_rag_chunks_created_at", "rag_chunks", ["created_at"])
    if op.get_bind().dialect.name == "postgresql":
        _create_index_if_missing(
            "rag_chunks_embedding_idx",
            "rag_chunks",
            ["embedding"],
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"lists": 100},
        )

    _create_index_if_missing("extracted_questions_source_id_idx", "extracted_questions", ["source_id"])
    _create_index_if_missing("extracted_questions_chapter_id_idx", "extracted_questions", ["chapter_id"])
    _create_index_if_missing("extracted_questions_topic_id_idx", "extracted_questions", ["topic_id"])
    _create_index_if_missing("extracted_questions_needs_review_idx", "extracted_questions", ["needs_review"])
    _create_index_if_missing("ix_extracted_questions_id", "extracted_questions", ["id"])
    _create_index_if_missing("ix_extracted_questions_created_at", "extracted_questions", ["created_at"])
    _create_index_if_missing("ix_extracted_questions_lesson_id", "extracted_questions", ["lesson_id"])


def upgrade() -> None:
    _create_pgvector_extension()
    _create_core_tables()
    _create_learning_tables()
    _create_content_tables()
    _create_chat_and_media_tables()
    _create_indexes()


def downgrade() -> None:
    for table_name in (
        "question_attempts",
        "chat_messages",
        "reels",
        "chat_sessions",
        "extracted_questions",
        "rag_chunks",
        "textbook_chunks",
        "ingestion_pages",
        "ingestion_jobs",
        "homework",
        "lesson_progress",
        "flashcard_progress",
        "user_progress",
        "quiz_attempts",
        "questions",
        "flashcards",
        "study_plans",
        "subscriptions",
        "user_interests",
        "student_profiles",
        "lessons",
        "device_tokens",
        "achievements",
        "chapters",
        "users",
        "topics",
        "interest_categories",
        "elements",
        "content_sources",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)
