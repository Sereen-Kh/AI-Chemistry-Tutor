"""Shared preference schemas for tutor presentation settings."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ExplanationMethod, LearningMode, StudentInterest, TeachingLevel


class TutorPreferenceFields(BaseModel):
    """Reusable preference fields for user/profile APIs."""

    teaching_level: TeachingLevel = TeachingLevel.STANDARD
    explanation_method: ExplanationMethod = ExplanationMethod.DIRECT
    learning_modes: list[LearningMode] = Field(default_factory=lambda: [LearningMode.TEXT])
    student_interests: list[StudentInterest] = Field(default_factory=list)

    @field_validator("learning_modes")
    @classmethod
    def ensure_text_mode(cls, value: list[LearningMode]) -> list[LearningMode]:
        modes = list(dict.fromkeys(value or [LearningMode.TEXT]))
        if LearningMode.TEXT not in modes:
            modes.insert(0, LearningMode.TEXT)
        return modes

    @field_validator("student_interests")
    @classmethod
    def drop_none_interest(cls, value: list[StudentInterest]) -> list[StudentInterest]:
        return [item for item in dict.fromkeys(value or []) if item != StudentInterest.NONE]
