"""Device-token APIs for mobile/web push notification registration."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.device import DeviceTokenRegisterRequest, DeviceTokenResponse
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["devices"])
push_tokens_router = APIRouter(prefix="/push-tokens", tags=["devices"])


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


@push_tokens_router.get("", response_model=list[DeviceTokenResponse])
async def list_push_tokens(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await device_service.list_device_tokens(db, user_id)


@push_tokens_router.post("", response_model=DeviceTokenResponse, status_code=201)
async def register_push_token(
    request: DeviceTokenRegisterRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await device_service.register_device_token(db, user_id, request)


@push_tokens_router.delete("/{token_id}", status_code=204)
async def delete_push_token(
    token_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await device_service.delete_device_token_by_id(db, user_id, token_id)
    return Response(status_code=204)
