"""Persist external web citations for Ask AI chat history.

Revision ID: 0014_ask_ai_memory_web_grounding
Revises: 0013_interest_personalization
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_ask_ai_memory_web_grounding"
down_revision = "0013_interest_personalization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("external_sources_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "external_sources_json")
