"""Endpoints for managing notifications and preferences."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.notification import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.services import notification_service

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List all notifications for the authenticated user."""
    return await notification_service.get_notifications(
        db,
        user_id,
        status=status,
        type=type,
        limit=limit,
        offset=offset,
    )


@router.get("/notifications/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve the total count of unread notifications for a user."""
    count = await notification_service.get_unread_count(db, user_id)
    return {"unread_count": count}


@router.patch("/notifications/{id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Mark a notification as read."""
    return await notification_service.mark_read(db, user_id, id)


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read_post(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk mark all unread notifications as read."""
    await notification_service.mark_all_read(db, user_id)
    return {"status": "success"}


@router.patch("/notifications/mark-all-read")
async def mark_all_notifications_read(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Bulk mark all unread notifications as read."""
    await notification_service.mark_all_read(db, user_id)
    return {"status": "success"}


@router.delete("/notifications/{id}", status_code=204)
async def delete_notification(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a notification."""
    await notification_service.delete_notification(db, user_id, id)
    return Response(status_code=204)


@router.get("/notification-preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Get the notification preference settings for a user."""
    return await notification_service.get_preferences(db, user_id)


@router.patch("/notification-preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    updates: NotificationPreferenceUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Update notification preferences."""
    return await notification_service.update_preferences(db, user_id, updates)


@router.post("/reminders/rebuild")
async def rebuild_reminders(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Rebuild study plan and exam reminder schedules."""
    await notification_service.rebuild_reminders(db, user_id)
    return {"status": "success", "message": "Reminder events rebuilt successfully"}


@router.post("/notifications/test", response_model=NotificationResponse)
async def send_test_notification(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create and push a short test notification to the current user."""
    return await notification_service.send_test_notification(db, user_id)


@router.post("/notifications/generate-due")
async def generate_due_notifications(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Generate due reminders for the current user from backend state."""
    counts = await notification_service.generate_due_reminders(db, user_id)
    return {"status": "success", "counts": counts}
