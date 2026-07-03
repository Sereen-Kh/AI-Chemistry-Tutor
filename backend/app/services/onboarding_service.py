"""Shared onboarding completion rules."""

from __future__ import annotations

from collections.abc import Iterable


def _has_non_empty_values(values: Iterable[object] | None) -> bool:
    if values is None:
        return False
    return any(str(getattr(value, "value", value)).strip() for value in values)


def is_onboarding_complete_values(
    *,
    student_interests: Iterable[object] | None,
    learning_modes: Iterable[object] | None,
    teaching_level: object | None,
    explanation_method: object | None,
) -> bool:
    """Infer onboarding completion without requiring a database migration."""

    return (
        _has_non_empty_values(student_interests)
        and _has_non_empty_values(learning_modes)
        and bool(str(getattr(teaching_level, "value", teaching_level or "")).strip())
        and bool(str(getattr(explanation_method, "value", explanation_method or "")).strip())
    )


def is_profile_onboarding_complete(profile: object | None) -> bool:
    if profile is None:
        return False
    return is_onboarding_complete_values(
        student_interests=getattr(profile, "student_interests", None),
        learning_modes=getattr(profile, "learning_modes", None),
        teaching_level=getattr(profile, "teaching_level", None),
        explanation_method=getattr(profile, "explanation_method", None),
    )


def is_user_onboarding_complete(user: object | None) -> bool:
    if user is None:
        return False
    profile = getattr(user, "__dict__", {}).get("student_profile")
    if profile is not None:
        return is_profile_onboarding_complete(profile)
    return is_onboarding_complete_values(
        student_interests=getattr(user, "student_interests", None),
        learning_modes=getattr(user, "learning_modes", None),
        teaching_level=getattr(user, "teaching_level", None),
        explanation_method=getattr(user, "explanation_method", None),
    )
