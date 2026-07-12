"""Admin-facing curriculum readiness schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CurriculumReadinessIssue(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    entity_type: Literal["artifact", "unit", "chapter", "lesson", "topic", "relationship"]
    message: str
    entity_id: int | str | None = None
    stable_id: str | None = None
    field: str | None = None
    expected: Any = None
    actual: Any = None


class CurriculumLessonMapping(BaseModel):
    stable_lesson_id: str
    unit_id: str
    db_lesson_id: int | None = None
    match_method: Literal["title", "order", "unmatched"]
    expected_title: str
    actual_title: str | None = None
    expected_page_start: int | None = None
    expected_page_end: int | None = None
    actual_page_start: int | None = None
    actual_page_end: int | None = None


class CurriculumReadinessCounts(BaseModel):
    expected_units: int = 0
    database_units: int = 0
    expected_chapters: int = 0
    database_chapters: int = 0
    expected_lessons: int = 0
    database_lessons: int = 0
    mapped_lessons: int = 0
    expected_topics: int = 0
    database_topics: int = 0
    linked_topics: int = 0
    errors: int = 0
    warnings: int = 0


class CurriculumReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    ready: bool
    checked_at: datetime
    reviewed_metadata_version: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    counts: CurriculumReadinessCounts
    lesson_mappings: list[CurriculumLessonMapping] = Field(default_factory=list)
    issues: list[CurriculumReadinessIssue] = Field(default_factory=list)

