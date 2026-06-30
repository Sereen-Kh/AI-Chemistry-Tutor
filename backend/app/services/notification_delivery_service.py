"""Push delivery abstraction for notification channels.

The database notification row is the source of truth. Push providers are a
best-effort delivery channel and must never prevent in-app persistence.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.device import DeviceToken
from app.models.notification import Notification

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PushDeliveryResult:
    token_id: int
    platform: str
    status: str
    error: str | None = None


def build_push_payload(notification: Notification) -> dict[str, Any]:
    """Build a short, non-sensitive push payload."""

    title = notification.title_ar or notification.title
    body = notification.body_ar or notification.message
    return {
        "title": title[:120],
        "body": body[:180],
        "data": {
            "notification_id": str(notification.id),
            "type": notification.type,
            "action_url": notification.action_url or "/notifications",
        },
    }


async def send_to_user(db: AsyncSession, user_id: int, notification: Notification) -> list[PushDeliveryResult]:
    """Send a persisted notification to all active user tokens."""

    result = await db.execute(
        select(DeviceToken)
        .where(DeviceToken.user_id == user_id, DeviceToken.is_active.is_(True))
        .order_by(DeviceToken.updated_at.desc())
    )
    tokens = list(result.scalars().all())
    payload = build_push_payload(notification)
    results: list[PushDeliveryResult] = []
    for token in tokens:
        try:
            results.append(await send_to_token(token, payload))
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            logger.exception("Push delivery failed for token %s", token.id)
            results.append(PushDeliveryResult(token.id, token.platform, "failed", str(exc)))
    return results


async def send_to_token(token: DeviceToken, payload: dict[str, Any]) -> PushDeliveryResult:
    """Route a push payload to the correct provider."""

    if token.platform == "expo":
        return await send_expo(token, payload)
    if token.platform in {"web", "android", "ios"}:
        return await send_fcm(token, payload)
    return PushDeliveryResult(token.id, token.platform, "skipped", "unsupported platform")


async def send_expo(token: DeviceToken, payload: dict[str, Any]) -> PushDeliveryResult:
    if not settings.expo_push_enabled:
        return PushDeliveryResult(token.id, token.platform, "skipped", "expo disabled")

    message = {
        "to": token.token,
        "title": payload["title"],
        "body": payload["body"],
        "data": payload["data"],
        "sound": "default",
    }
    async with httpx.AsyncClient(timeout=settings.notification_push_timeout_seconds) as client:
        response = await client.post("https://exp.host/--/api/v2/push/send", json=message)
    if response.status_code >= 400:
        return PushDeliveryResult(token.id, token.platform, "failed", response.text[:500])
    return PushDeliveryResult(token.id, token.platform, "sent")


def _fcm_access_token() -> tuple[str | None, str | None]:
    """Return OAuth token and project id for FCM v1 if configured."""

    if not settings.firebase_service_account_json:
        return None, None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except Exception:
        return None, None

    try:
        info = json.loads(settings.firebase_service_account_json)
        project_id = settings.firebase_project_id or info.get("project_id")
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(Request())
        return credentials.token, project_id
    except Exception:
        logger.exception("Failed to build Firebase credentials")
        return None, None


async def send_fcm(token: DeviceToken, payload: dict[str, Any]) -> PushDeliveryResult:
    access_token, project_id = _fcm_access_token()
    if not access_token or not project_id:
        return PushDeliveryResult(token.id, token.platform, "skipped", "firebase not configured")

    message = {
        "message": {
            "token": token.token,
            "notification": {
                "title": payload["title"],
                "body": payload["body"],
            },
            "data": {key: str(value) for key, value in payload["data"].items()},
        }
    }
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    async with httpx.AsyncClient(timeout=settings.notification_push_timeout_seconds) as client:
        response = await client.post(url, json=message, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code >= 400:
        return PushDeliveryResult(token.id, token.platform, "failed", response.text[:500])
    return PushDeliveryResult(token.id, token.platform, "sent")
