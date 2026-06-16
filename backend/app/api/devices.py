"""Device-token APIs for mobile/web push notification registration."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.device import DeviceTokenRegisterRequest, DeviceTokenResponse
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceTokenResponse])
async def list_devices(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await device_service.list_device_tokens(db, user_id)


@router.post("/register", response_model=DeviceTokenResponse, status_code=201)
async def register_device(
    request: DeviceTokenRegisterRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await device_service.register_device_token(db, user_id, request)


@router.delete("/{token}", status_code=204)
async def delete_device(
    token: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await device_service.delete_device_token(db, user_id, token)
    return Response(status_code=204)
