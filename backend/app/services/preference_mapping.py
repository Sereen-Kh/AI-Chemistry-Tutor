"""Preference validation and legacy mapping for tutor presentation settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.models.enums import ExplanationMethod, LearningMode, StudentInterest, TeachingLevel

DEFAULT_TEACHING_LEVEL = TeachingLevel.STANDARD.value
DEFAULT_EXPLANATION_METHOD = ExplanationMethod.DIRECT.value
DEFAULT_LEARNING_MODES = [LearningMode.TEXT.value]
DEFAULT_STUDENT_INTERESTS: list[str] = []

_LEGACY_TEACHING_STYLE_MAP = {
    "beginner": (TeachingLevel.SIMPLE.value, ExplanationMethod.DIRECT.value),
    "Beginner": (TeachingLevel.SIMPLE.value, ExplanationMethod.DIRECT.value),
    "step_by_step": (TeachingLevel.STANDARD.value, ExplanationMethod.STEP_BY_STEP.value),
    "Step-By-Step": (TeachingLevel.STANDARD.value, ExplanationMethod.STEP_BY_STEP.value),
    "step-by-step": (TeachingLevel.STANDARD.value, ExplanationMethod.STEP_BY_STEP.value),
    "academic": (TeachingLevel.ACADEMIC.value, ExplanationMethod.DIRECT.value),
    "Academic": (TeachingLevel.ACADEMIC.value, ExplanationMethod.DIRECT.value),
    "real_life_examples": (TeachingLevel.STANDARD.value, ExplanationMethod.REAL_LIFE_EXAMPLE.value),
    "real_life": (TeachingLevel.STANDARD.value, ExplanationMethod.REAL_LIFE_EXAMPLE.value),
    "Real-life style": (TeachingLevel.STANDARD.value, ExplanationMethod.REAL_LIFE_EXAMPLE.value),
    "real-life style": (TeachingLevel.STANDARD.value, ExplanationMethod.REAL_LIFE_EXAMPLE.value),
    "real_life_style": (TeachingLevel.STANDARD.value, ExplanationMethod.REAL_LIFE_EXAMPLE.value),
    "visual": (TeachingLevel.STANDARD.value, ExplanationMethod.DIRECT.value),
    "fast_summary": (TeachingLevel.STANDARD.value, ExplanationMethod.EXAM_MODE.value),
}

_LEGACY_ANSWER_FORMAT_MAP = {
    "text": [LearningMode.TEXT.value],
    "Text": [LearningMode.TEXT.value],
    "images": [LearningMode.TEXT.value, LearningMode.IMAGE.value],
    "image": [LearningMode.TEXT.value, LearningMode.IMAGE.value],
    "Text + image": [LearningMode.TEXT.value, LearningMode.IMAGE.value],
    "Text + Image": [LearningMode.TEXT.value, LearningMode.IMAGE.value],
    "text + image": [LearningMode.TEXT.value, LearningMode.IMAGE.value],
    "text_image": [LearningMode.TEXT.value, LearningMode.IMAGE.value],
    "voice": [LearningMode.TEXT.value, LearningMode.AUDIO.value],
    "Voice": [LearningMode.TEXT.value, LearningMode.AUDIO.value],
    "audio": [LearningMode.TEXT.value, LearningMode.AUDIO.value],
    "video": [LearningMode.TEXT.value, LearningMode.VIDEO.value],
    "Video": [LearningMode.TEXT.value, LearningMode.VIDEO.value],
}


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _key(value: object) -> str:
    return _value(value).strip().lower().replace(" ", "_").replace("-", "_")


@dataclass(frozen=True)
class TutorPreferences:
    """Resolved per-request tutoring presentation preferences."""

    teaching_level: str = DEFAULT_TEACHING_LEVEL
    explanation_method: str = DEFAULT_EXPLANATION_METHOD
    learning_modes: list[str] = field(default_factory=lambda: list(DEFAULT_LEARNING_MODES))
    student_interests: list[str] = field(default_factory=list)
    requested_learning_modes: list[str] | None = None

    def as_diagnostics(self) -> dict[str, object]:
        return {
            "teaching_level": self.teaching_level,
            "explanation_method": self.explanation_method,
            "learning_modes": self.learning_modes,
            "student_interests": self.student_interests,
            "requested_learning_modes": self.requested_learning_modes,
        }


def normalize_teaching_level(value: str | None) -> str:
    normalized = _value(value)
    if normalized in {item.value for item in TeachingLevel}:
        return normalized
    return DEFAULT_TEACHING_LEVEL


def normalize_explanation_method(value: str | None) -> str:
    normalized = _value(value)
    if normalized in {item.value for item in ExplanationMethod}:
        return normalized
    return DEFAULT_EXPLANATION_METHOD


def normalize_learning_modes(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return list(DEFAULT_LEARNING_MODES)
    if isinstance(values, str):
        mapped = _LEGACY_ANSWER_FORMAT_MAP.get(values)
        if mapped:
            return mapped
        values = [values]
    allowed = {item.value for item in LearningMode}
    modes: list[str] = []
    for value in values:
        raw = _value(value)
        mode = LearningMode.IMAGE.value if raw == LearningMode.IMAGES.value else raw
        if mode in allowed and mode not in modes:
            modes.append(mode)
    if LearningMode.TEXT.value not in modes:
        modes.insert(0, LearningMode.TEXT.value)
    return modes or list(DEFAULT_LEARNING_MODES)


def normalize_student_interests(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    allowed = {item.value for item in StudentInterest}
    interests = [_value(value) for value in values if _value(value) in allowed and _value(value) != StudentInterest.NONE.value]
    return sorted(set(interests))


def map_legacy_teaching_style(value: str | None) -> tuple[str, str]:
    """Map old single-axis teaching_style to teaching_level + explanation_method."""
    raw = _value(value)
    return _LEGACY_TEACHING_STYLE_MAP.get(
        raw,
        _LEGACY_TEACHING_STYLE_MAP.get(_key(raw), (DEFAULT_TEACHING_LEVEL, DEFAULT_EXPLANATION_METHOD)),
    )


def map_legacy_answer_format(value: str | None) -> list[str]:
    """Map old answer_format to the new multi-mode output model."""
    return normalize_learning_modes(_LEGACY_ANSWER_FORMAT_MAP.get(_value(value), value))


def legacy_teaching_style_from_new(teaching_level: str, explanation_method: str) -> str:
    """Best-effort legacy value for old clients."""
    if explanation_method == ExplanationMethod.STEP_BY_STEP.value:
        return "step_by_step"
    if explanation_method == ExplanationMethod.REAL_LIFE_EXAMPLE.value:
        return "real_life_examples"
    if explanation_method == ExplanationMethod.EXAM_MODE.value or teaching_level == TeachingLevel.ACADEMIC.value:
        return "academic"
    if teaching_level == TeachingLevel.SIMPLE.value:
        return "beginner"
    return "real_life_examples"


def legacy_answer_format_from_modes(learning_modes: Iterable[str]) -> str:
    """Best-effort legacy answer_format for old clients."""
    modes = set(normalize_learning_modes(learning_modes))
    if LearningMode.VIDEO.value in modes or LearningMode.REEL.value in modes:
        return LearningMode.VIDEO.value
    if LearningMode.IMAGE.value in modes:
        return LearningMode.IMAGES.value
    if LearningMode.AUDIO.value in modes:
        return LearningMode.AUDIO.value
    return LearningMode.TEXT.value


def preferences_from_user(
    user,
    *,
    teaching_level: str | None = None,
    explanation_method: str | None = None,
    learning_modes: list[str] | None = None,
    student_interests: list[str] | None = None,
) -> TutorPreferences:
    """Resolve request overrides over stored user defaults with legacy fallback."""
    profile = getattr(user, "__dict__", {}).get("student_profile")
    legacy_level, legacy_method = map_legacy_teaching_style(getattr(user, "teaching_style", None))
    stored_level = normalize_teaching_level(
        getattr(profile, "teaching_level", None) if profile is not None else getattr(user, "teaching_level", None) or legacy_level
    )
    stored_method = normalize_explanation_method(
        getattr(profile, "explanation_method", None)
        if profile is not None
        else getattr(user, "explanation_method", None) or legacy_method
    )
    stored_modes = normalize_learning_modes(
        (getattr(profile, "learning_modes", None) if profile is not None else getattr(user, "learning_modes", None))
        or map_legacy_answer_format(getattr(user, "answer_format", None))
    )
    stored_interests = normalize_student_interests(
        getattr(profile, "student_interests", None) if profile is not None else getattr(user, "student_interests", None)
    )

    return TutorPreferences(
        teaching_level=normalize_teaching_level(teaching_level or stored_level),
        explanation_method=normalize_explanation_method(explanation_method or stored_method),
        learning_modes=normalize_learning_modes(learning_modes if learning_modes is not None else stored_modes),
        student_interests=normalize_student_interests(
            student_interests if student_interests is not None else stored_interests
        ),
        requested_learning_modes=normalize_learning_modes(learning_modes) if learning_modes is not None else None,
    )


def apply_user_preference_updates(user, updates: dict) -> None:
    """Apply new and legacy preference updates to a user model in place."""
    if "teaching_style" in updates and updates["teaching_style"] is not None:
        level, method = map_legacy_teaching_style(updates["teaching_style"])
        user.teaching_style = _value(updates["teaching_style"])
        user.teaching_level = level
        user.explanation_method = method
    if "answer_format" in updates and updates["answer_format"] is not None:
        user.answer_format = _value(updates["answer_format"])
        user.learning_modes = map_legacy_answer_format(updates["answer_format"])
    if "teaching_level" in updates and updates["teaching_level"] is not None:
        user.teaching_level = normalize_teaching_level(updates["teaching_level"])
    if "explanation_method" in updates and updates["explanation_method"] is not None:
        user.explanation_method = normalize_explanation_method(updates["explanation_method"])
    if "learning_modes" in updates and updates["learning_modes"] is not None:
        user.learning_modes = normalize_learning_modes(updates["learning_modes"])
    if "student_interests" in updates and updates["student_interests"] is not None:
        user.student_interests = normalize_student_interests(updates["student_interests"])
    if "teaching_level" in updates or "explanation_method" in updates:
        user.teaching_style = legacy_teaching_style_from_new(user.teaching_level, user.explanation_method)
    if "learning_modes" in updates:
        user.answer_format = legacy_answer_format_from_modes(user.learning_modes)
