"""Canonical reviewed curriculum catalog and import report schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReviewedTopic(BaseModel):
    stable_id: str
    title_ar: str
    order: int
    page_start: int
    page_end: int
    quality_status: Literal["ready", "needs_review", "blocked"]
    quality_score: float

    @model_validator(mode="after")
    def validate_range(self):
        if self.page_start > self.page_end:
            raise ValueError("topic page_start must be <= page_end")
        return self


class ReviewedLesson(BaseModel):
    stable_id: str
    lesson_number: int
    title_ar: str
    order: int
    printed_page_start: int
    printed_page_end: int
    pdf_page_start: int | None = None
    pdf_page_end: int | None = None
    quality_status: Literal["ready", "needs_review", "blocked"]
    quality_score: float
    duration_min: int = 45
    topics: list[ReviewedTopic] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self):
        if self.printed_page_start > self.printed_page_end:
            raise ValueError("lesson printed_page_start must be <= printed_page_end")
        return self


class ReviewedChapter(BaseModel):
    stable_id: str
    chapter_number: int
    title_ar: str
    order: int
    lessons: list[ReviewedLesson] = Field(min_length=1)


class ReviewedUnit(BaseModel):
    stable_id: str
    unit_number: int
    semester: int
    title_ar: str
    order: int
    chapters: list[ReviewedChapter] = Field(min_length=1)


class ReviewedCurriculumCatalog(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    source_slug: Literal["syria_grade_9_chemistry"] = "syria_grade_9_chemistry"
    grade: Literal["grade_9"] = "grade_9"
    subject: Literal["chemistry"] = "chemistry"
    source_type: Literal["textbook"] = "textbook"
    status: Literal["reviewed"] = "reviewed"
    reviewed_metadata_version: str
    generated_at: datetime
    source_paths: list[str]
    units: list[ReviewedUnit] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_stable_ids(self):
        ids: list[str] = []
        for unit in self.units:
            ids.append(unit.stable_id)
            for chapter in unit.chapters:
                ids.append(chapter.stable_id)
                for lesson in chapter.lessons:
                    ids.append(lesson.stable_id)
                    ids.extend(topic.stable_id for topic in lesson.topics)
        if len(ids) != len(set(ids)):
            raise ValueError("stable curriculum IDs must be globally unique")
        return self


class CurriculumImportCounts(BaseModel):
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    conflicting: int = 0
    mappings_inserted: int = 0
    mappings_updated: int = 0
    mappings_unchanged: int = 0


class CurriculumImportConflict(BaseModel):
    code: str
    entity_type: str
    stable_id: str
    message: str
    existing_entity_id: int | None = None


class CurriculumImportReport(BaseModel):
    status: Literal["dry_run", "applied", "conflict", "failed"]
    dry_run: bool
    catalog_path: str
    reviewed_metadata_version: str
    started_at: datetime
    completed_at: datetime
    counts: CurriculumImportCounts
    conflicts: list[CurriculumImportConflict] = Field(default_factory=list)
    stable_id_mapping: dict[str, int] = Field(default_factory=dict)

