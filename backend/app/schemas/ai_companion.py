"""Schemas for the context-aware AI companion placeholder API."""

from typing import Any

from pydantic import BaseModel, Field


class LearningContextPayload(BaseModel):
    userId: str | None = None
    currentPage: str
    activeSemester: int | None = None
    activeUnitId: int | None = None
    activeChapterId: int | None = None
    activeLessonId: int | None = None
    activeTopicId: int | None = None
    activeUnitTitleAr: str | None = None
    activeChapterTitleAr: str | None = None
    activeLessonTitleAr: str | None = None
    activeTopicTitleAr: str | None = None
    progressPercent: int | float | None = None
    dailyMission: dict[str, Any] | None = None
    weakTopics: list[dict[str, Any]] = Field(default_factory=list)
    nextExamDate: str | None = None
    scrollSection: str | None = None


class CompanionRequest(BaseModel):
    message: str | None = None
    context: LearningContextPayload
    preferred_language: str = "ar"
    response_mode: str = "action"


class CompanionActionResponse(BaseModel):
    id: str
    label: str
    kind: str
    targetRoute: str | None = None
    description: str | None = None


class CompanionResponse(BaseModel):
    message: str
    suggestedActions: list[CompanionActionResponse] = Field(default_factory=list)
    targetRoute: str | None = None
    responseMode: str | None = None
