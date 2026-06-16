"""Add multi-dimensional tutor preferences.

Revision ID: 0002_preference_dimensions
Revises: 0001_initial_schema
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_preference_dimensions"
down_revision = "0001_initial_schema"
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


def _add_preference_columns(table_name: str) -> None:
    if not _has_table(table_name):
        return
    columns = [
        ("teaching_level", sa.String(length=30)),
        ("explanation_method", sa.String(length=40)),
        ("learning_modes", sa.JSON()),
        ("student_interests", sa.JSON()),
    ]
    missing = [(name, column_type) for name, column_type in columns if not _has_column(table_name, name)]
    if not missing:
        return
    with op.batch_alter_table(table_name) as batch_op:
        for name, column_type in missing:
            batch_op.add_column(sa.Column(name, column_type, nullable=True))


def _drop_preference_columns(table_name: str) -> None:
    if not _has_table(table_name):
        return
    existing = [
        column
        for column in ("student_interests", "learning_modes", "explanation_method", "teaching_level")
        if _has_column(table_name, column)
    ]
    if not existing:
        return
    with op.batch_alter_table(table_name) as batch_op:
        for column in existing:
            batch_op.drop_column(column)


def upgrade() -> None:
    _add_preference_columns("users")
    _add_preference_columns("student_profiles")

    bind = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("teaching_style", sa.String),
        sa.column("answer_format", sa.String),
        sa.column("teaching_level", sa.String),
        sa.column("explanation_method", sa.String),
        sa.column("learning_modes", sa.JSON),
        sa.column("student_interests", sa.JSON),
    )
    for row in bind.execute(sa.select(users.c.id, users.c.teaching_style, users.c.answer_format)).mappings():
        style = row["teaching_style"]
        answer_format = row["answer_format"]
        teaching_level = "simple" if style == "beginner" else "academic" if style == "academic" else "standard"
        explanation_method = (
            "step_by_step"
            if style == "step_by_step"
            else "real_life_example"
            if style == "real_life_examples"
            else "direct"
        )
        learning_modes = (
            ["text", "image"]
            if answer_format in {"images", "image"}
            else ["text", "video"]
            if answer_format == "video"
            else ["text", "audio"]
            if answer_format in {"audio", "voice"}
            else ["text"]
        )
        bind.execute(
            users.update()
            .where(users.c.id == row["id"])
            .values(
                teaching_level=teaching_level,
                explanation_method=explanation_method,
                learning_modes=learning_modes,
                student_interests=[],
            )
        )

    profiles = sa.table(
        "student_profiles",
        sa.column("id", sa.Integer),
        sa.column("learning_style", sa.String),
        sa.column("teaching_level", sa.String),
        sa.column("explanation_method", sa.String),
        sa.column("learning_modes", sa.JSON),
        sa.column("student_interests", sa.JSON),
    )
    for row in bind.execute(sa.select(profiles.c.id, profiles.c.learning_style)).mappings():
        style = row["learning_style"]
        bind.execute(
            profiles.update()
            .where(profiles.c.id == row["id"])
            .values(
                teaching_level="simple" if style == "beginner" else "academic" if style == "academic" else "standard",
                explanation_method=(
                    "step_by_step"
                    if style == "step_by_step"
                    else "real_life_example"
                    if style == "real_life_examples"
                    else "direct"
                ),
                learning_modes=["text"],
                student_interests=[],
            )
        )


def downgrade() -> None:
    _drop_preference_columns("student_profiles")
    _drop_preference_columns("users")
