"""Stable reviewed IDs mapped to numeric curriculum entity IDs."""

from sqlalchemy import Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin


class CurriculumEntityMapping(Base, TimestampMixin):
    __tablename__ = "curriculum_entity_mappings"
    __table_args__ = (
        UniqueConstraint("entity_type", "stable_id", name="uq_curriculum_mapping_type_stable"),
        Index("ix_curriculum_mapping_type_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    stable_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_metadata_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

