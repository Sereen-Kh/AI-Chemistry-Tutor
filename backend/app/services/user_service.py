"""Async user service functions."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.student_profile import StudentProfile
from app.services.preference_mapping import apply_user_preference_updates, legacy_teaching_style_from_new


async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def update_user(db: AsyncSession, user_id: int, updates: dict) -> User:
    user = await get_user(db, user_id)
    apply_user_preference_updates(user, updates)
    handled = {
        "teaching_style",
        "answer_format",
        "teaching_level",
        "explanation_method",
        "learning_modes",
        "student_interests",
    }
    for field, value in updates.items():
        if field not in handled and value is not None and hasattr(user, field):
            setattr(user, field, value)
    if handled.intersection(updates):
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = StudentProfile(user_id=user_id)
            db.add(profile)
        profile.grade = user.grade
        profile.subject = user.subject
        profile.learning_style = legacy_teaching_style_from_new(user.teaching_level, user.explanation_method)
        profile.teaching_level = user.teaching_level
        profile.explanation_method = user.explanation_method
        profile.learning_modes = user.learning_modes
        profile.student_interests = user.student_interests
        profile.preferred_language = user.language
    await db.commit()
    await db.refresh(user)
    return user
