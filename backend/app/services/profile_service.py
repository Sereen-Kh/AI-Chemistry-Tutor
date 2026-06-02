"""Student profile service functions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_profile import StudentProfile


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
    for field, value in updates.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile
