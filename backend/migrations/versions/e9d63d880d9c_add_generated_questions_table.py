"""add generated questions table

Revision ID: e9d63d880d9c
Revises: c097248463e1
Create Date: 2026-07-21 22:23:15.852066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9d63d880d9c'
down_revision: Union[str, Sequence[str], None] = 'c097248463e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():

    op.create_table(
        "generated_questions",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "lesson",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "question_type",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "difficulty",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "question",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "options",
            postgresql.JSONB(),
            nullable=False,
        ),

        sa.Column(
            "answer",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "explanation",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_generated_questions_lesson",
        "generated_questions",
        ["lesson"],
    )

    op.create_index(
        "ix_generated_questions_question_type",
        "generated_questions",
        ["question_type"],
    )

    op.create_index(
        "ix_generated_questions_difficulty",
        "generated_questions",
        ["difficulty"],
    )


def downgrade():

    op.drop_index(
        "ix_generated_questions_difficulty",
        table_name="generated_questions",
    )

    op.drop_index(
        "ix_generated_questions_question_type",
        table_name="generated_questions",
    )

    op.drop_index(
        "ix_generated_questions_lesson",
        table_name="generated_questions",
    )

    op.drop_table("generated_questions")
