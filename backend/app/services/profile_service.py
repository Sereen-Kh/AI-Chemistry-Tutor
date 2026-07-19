"""Student profile service functions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.interest_service import sync_user_interests_async, validate_interest_keys
from app.services.preference_mapping import (
    apply_user_preference_updates,
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
    user = await db.get(User, user_id)
    profile = StudentProfile(
        user_id=user_id,
        grade=getattr(user, "grade", "grade_9"),
        subject=getattr(user, "subject", "chemistry"),
        learning_style=getattr(user, "teaching_style", None) or "real_life_examples",
        teaching_level=normalize_teaching_level(getattr(user, "teaching_level", None)),
        explanation_method=normalize_explanation_method(getattr(user, "explanation_method", None)),
        learning_modes=normalize_learning_modes(getattr(user, "learning_modes", None)),
        student_interests=normalize_student_interests(getattr(user, "student_interests", None)),
        preferred_language=getattr(user, "language", "ar"),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


def _sync_user_from_profile(user: User | None, profile: StudentProfile) -> None:
    if user is None:
        return
    user.grade = profile.grade
    user.subject = profile.subject
    user.language = profile.preferred_language
    apply_user_preference_updates(
        user,
        {
            "teaching_style": profile.learning_style,
            "teaching_level": profile.teaching_level,
            "explanation_method": profile.explanation_method,
            "learning_modes": profile.learning_modes,
            "student_interests": profile.student_interests,
        },
    )


async def upsert_profile(db: AsyncSession, user_id: int, updates: dict) -> StudentProfile:
    profile = await get_or_create_profile(db, user_id)
    interest_keys = None
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
        interest_keys = validate_interest_keys(updates["student_interests"])
        profile.student_interests = interest_keys
    if updates.get("teaching_level") is not None or updates.get("explanation_method") is not None:
        profile.learning_style = legacy_teaching_style_from_new(profile.teaching_level, profile.explanation_method)
    if updates.get("learning_memory_enabled") is not None:
        metadata = dict(profile.metadata_json) if isinstance(profile.metadata_json, dict) else {}
        metadata["learning_memory_enabled"] = bool(updates["learning_memory_enabled"])
        profile.metadata_json = metadata
    handled = {
        "learning_style",
        "teaching_level",
        "explanation_method",
        "learning_modes",
        "student_interests",
        "learning_memory_enabled",
    }
    for field, value in updates.items():
        if field not in handled and hasattr(profile, field):
            setattr(profile, field, value)
    user = await db.get(User, user_id)
    _sync_user_from_profile(user, profile)
    if interest_keys is not None and user is not None:
        await sync_user_interests_async(
            db,
            user=user,
            profile=profile,
            interest_keys=interest_keys,
        )
    await db.commit()
    await db.refresh(profile)
    return profile
