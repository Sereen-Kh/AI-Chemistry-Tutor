"""Student profile service functions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_profile import StudentProfile
from app.services.preference_mapping import (
    legacy_teaching_style_from_new,
    map_legacy_teaching_style,
    normalize_explanation_method,
    normalize_learning_modes,
    normalize_student_interests,
    normalize_teaching_level,
)


def _raw_value(value: object) -> str:
    return str(getattr(value, "value", value))


async def get_or_create_profile(db: AsyncSession, user_id: int) -> StudentProfile:
    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile:
        return profile
    profile = StudentProfile(user_id=user_id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def upsert_profile(db: AsyncSession, user_id: int, updates: dict) -> StudentProfile:
    profile = await get_or_create_profile(db, user_id)
    if updates.get("learning_style") is not None:
        raw_style = _raw_value(updates["learning_style"])
        level, method = map_legacy_teaching_style(raw_style)
        profile.learning_style = raw_style
        profile.teaching_level = level
        profile.explanation_method = method
    if updates.get("teaching_level") is not None:
        profile.teaching_level = normalize_teaching_level(_raw_value(updates["teaching_level"]))
    if updates.get("explanation_method") is not None:
        profile.explanation_method = normalize_explanation_method(_raw_value(updates["explanation_method"]))
    if updates.get("learning_modes") is not None:
        profile.learning_modes = normalize_learning_modes(updates["learning_modes"])
    if updates.get("student_interests") is not None:
        profile.student_interests = normalize_student_interests(updates["student_interests"])
    if updates.get("teaching_level") is not None or updates.get("explanation_method") is not None:
        profile.learning_style = legacy_teaching_style_from_new(profile.teaching_level, profile.explanation_method)
    handled = {"learning_style", "teaching_level", "explanation_method", "learning_modes", "student_interests"}
    for field, value in updates.items():
        if field not in handled and hasattr(profile, field):
            setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile
