"""Shared enums for user preferences and learning configuration."""

from enum import Enum


class TeachingStyle(str, Enum):
    """Legacy single-axis teaching style kept for API compatibility."""

    BEGINNER = "beginner"
    STEP_BY_STEP = "step_by_step"
    ACADEMIC = "academic"
    FAST_SUMMARY = "fast_summary"
    VISUAL = "visual"
    REAL_LIFE_EXAMPLES = "real_life_examples"


class TeachingLevel(str, Enum):
    """Student-facing difficulty/formality level for explanation text."""

    SIMPLE = "simple"
    STANDARD = "standard"
    ACADEMIC = "academic"


class ExplanationMethod(str, Enum):
    """How the tutor should structure an explanation."""

    DIRECT = "direct"
    STEP_BY_STEP = "step_by_step"
    HINTS_FIRST = "hints_first"
    EXAM_MODE = "exam_mode"
    REAL_LIFE_EXAMPLE = "real_life_example"


class LearningMode(str, Enum):
    """Output/learning mode.

    `IMAGES` is retained as a deprecated legacy value used by old clients.
    New clients should use `IMAGE`.
    """

    TEXT = "text"
    IMAGE = "image"
    IMAGES = "images"
    AUDIO = "audio"
    INTERACTIVE = "interactive"
    VIDEO = "video"
    REEL = "reel"
    QUIZ = "quiz"
    FLASHCARDS = "flashcards"


class StudentInterest(str, Enum):
    """Allowed personalization interests for safe analogies only."""

    FOOTBALL = "football"
    CARS = "cars"
    COOKING = "cooking"
    GAMING = "gaming"
    DAILY_LIFE = "daily_life"
    LABORATORY = "laboratory"
    NATURE = "nature"
    NONE = "none"
