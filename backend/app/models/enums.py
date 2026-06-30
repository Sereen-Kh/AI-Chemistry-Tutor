"""Shared enums for user preferences and learning configuration."""

from enum import Enum


class TeachingStyle(str, Enum):
    """Teaching style enum accepting both backend-native and frontend values.

    Backend-native values: beginner, step_by_step, academic, fast_summary,
    visual, real_life_examples.
    Frontend values (aliases): simple ≈ beginner, real_life ≈ real_life_examples,
    exam (exam-focused style).
    """

    BEGINNER = "beginner"
    STEP_BY_STEP = "step_by_step"
    ACADEMIC = "academic"
    FAST_SUMMARY = "fast_summary"
    VISUAL = "visual"
    REAL_LIFE_EXAMPLES = "real_life_examples"
    # Frontend-sent aliases — accepted by the API so clients don't need remapping.
    SIMPLE = "simple"
    REAL_LIFE = "real_life"
    EXAM = "exam"


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
