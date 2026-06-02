"""Async user service functions."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def update_user(db: AsyncSession, user_id: int, updates: dict) -> User:
    user = await get_user(db, user_id)
    for field, value in updates.items():
        if value is not None and hasattr(user, field):
            setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
