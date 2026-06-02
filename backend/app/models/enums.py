"""Shared enums for user preferences and learning configuration."""

from enum import Enum


class TeachingStyle(str, Enum):
    BEGINNER = "beginner"
    STEP_BY_STEP = "step_by_step"
    ACADEMIC = "academic"
    FAST_SUMMARY = "fast_summary"
    VISUAL = "visual"
    REAL_LIFE_EXAMPLES = "real_life_examples"


class LearningMode(str, Enum):
    TEXT = "text"
    IMAGES = "images"
    INTERACTIVE = "interactive"
    VIDEO = "video"
