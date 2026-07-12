"""Add stable reviewed curriculum entity mappings.

Revision ID: 0012_curriculum_entity_mappings
Revises: 0011_flashcards_product_model
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_curriculum_entity_mappings"
down_revision = "0011_flashcards_product_model"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if _has_table("curriculum_entity_mappings"):
        return
    op.create_table(
        "curriculum_entity_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("stable_id", sa.String(length=160), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_metadata_version", sa.String(length=80), nullable=False),
        sa.Column("source_path", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "stable_id", name="uq_curriculum_mapping_type_stable"),
    )
    op.create_index(
        "ix_curriculum_mapping_type_entity",
        "curriculum_entity_mappings",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_curriculum_entity_mappings_entity_type",
        "curriculum_entity_mappings",
        ["entity_type"],
    )
    op.create_index(
        "ix_curriculum_entity_mappings_stable_id",
        "curriculum_entity_mappings",
        ["stable_id"],
    )
    op.create_index(
        "ix_curriculum_entity_mappings_reviewed_metadata_version",
        "curriculum_entity_mappings",
        ["reviewed_metadata_version"],
    )


def downgrade() -> None:
    if _has_table("curriculum_entity_mappings"):
        op.drop_table("curriculum_entity_mappings")

