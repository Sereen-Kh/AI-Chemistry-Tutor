"""User API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.users import UserPublicResponse, UserUpdateRequest
from app.schemas.notification import NotificationPreferenceResponse, NotificationPreferenceUpdate
from app.services import notification_service
from app.services.user_service import get_user, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublicResponse)
async def get_me(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_async_db)):
    return await get_user(db, user_id)


@router.patch("/me", response_model=UserPublicResponse)
async def update_me(
    request: UserUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await update_user(db, user_id, request.model_dump(exclude_unset=True))


@router.get("/me/notification-settings", response_model=NotificationPreferenceResponse)
async def get_my_notification_settings(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await notification_service.get_preferences(db, user_id)


@router.patch("/me/notification-settings", response_model=NotificationPreferenceResponse)
async def update_my_notification_settings(
    request: NotificationPreferenceUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await notification_service.update_preferences(db, user_id, request)
