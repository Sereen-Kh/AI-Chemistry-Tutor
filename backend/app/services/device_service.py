"""Device-token service for push notification registration."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import DeviceToken
from app.schemas.device import DeviceTokenRegisterRequest


async def register_device_token(
    db: AsyncSession,
    user_id: int,
    request: DeviceTokenRegisterRequest,
) -> DeviceToken:
    result = await db.execute(select(DeviceToken).where(DeviceToken.token == request.token))
    existing = result.scalar_one_or_none()
    if existing:
        existing.user_id = user_id
        existing.platform = request.platform
        await db.commit()
        await db.refresh(existing)
        return existing

    token = DeviceToken(user_id=user_id, token=request.token, platform=request.platform)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def list_device_tokens(db: AsyncSession, user_id: int) -> list[DeviceToken]:
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.user_id == user_id).order_by(DeviceToken.updated_at.desc())
    )
    return list(result.scalars().all())


async def delete_device_token(db: AsyncSession, user_id: int, token: str) -> None:
    result = await db.execute(select(DeviceToken).where(DeviceToken.token == token))
    item = result.scalar_one_or_none()
    if item is None or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Device token not found")
    await db.delete(item)
    await db.commit()
