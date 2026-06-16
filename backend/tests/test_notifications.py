"""Unit tests for the Reminder Notification System."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.main import app
from app.schemas.notification import NotificationPreferenceUpdate
from app.workers.notification_tasks import check_pending_reminders


@pytest.fixture()
def notifications_client(monkeypatch: pytest.MonkeyPatch):
    """FastAPI client with auth/DB dependencies and service calls isolated."""

    async def fake_db():
        yield object()

    app.dependency_overrides[get_current_user_id] = lambda: 10
    app.dependency_overrides[get_async_db] = fake_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
        app.dependency_overrides.pop(get_async_db, None)


def test_preference_schema_valid_time() -> None:
    """Verify that preference schema accepts HH:MM format."""
    pref = NotificationPreferenceUpdate(reminder_time_local="14:30", timezone="Asia/Damascus")
    assert pref.reminder_time_local == "14:30"
    assert pref.timezone == "Asia/Damascus"


def test_preference_schema_invalid_time() -> None:
    """Verify that preference schema rejects invalid formats."""
    with pytest.raises(ValidationError):
        NotificationPreferenceUpdate(reminder_time_local="8:00")
    with pytest.raises(ValidationError):
        NotificationPreferenceUpdate(reminder_time_local="24:000")
    with pytest.raises(ValidationError):
        NotificationPreferenceUpdate(reminder_time_local="noon")


def test_notifications_api_list_and_unread_count(
    notifications_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the main notification read endpoints are exposed and typed."""

    now = datetime.now(timezone.utc)

    async def fake_get_notifications(_db, user_id: int):
        assert user_id == 10
        return [
            SimpleNamespace(
                id=1,
                user_id=10,
                type="exam_reminder",
                title="متبقي 7 أيام على الامتحان!",
                message="راجع خطة الامتحان.",
                status="unread",
                priority="high",
                scheduled_for=now,
                delivered_at=now,
                read_at=None,
                action_url="/study-plan",
                metadata_json={"source_type": "exam", "source_id": "1"},
                created_at=now,
                updated_at=now,
            )
        ]

    async def fake_unread_count(_db, user_id: int):
        assert user_id == 10
        return 1

    monkeypatch.setattr("app.services.notification_service.get_notifications", fake_get_notifications)
    monkeypatch.setattr("app.services.notification_service.get_unread_count", fake_unread_count)

    list_response = notifications_client.get("/api/v1/notifications")
    assert list_response.status_code == 200
    assert list_response.json()[0]["type"] == "exam_reminder"
    assert list_response.json()[0]["status"] == "unread"

    count_response = notifications_client.get("/api/v1/notifications/unread-count")
    assert count_response.status_code == 200
    assert count_response.json() == {"unread_count": 1}


def test_notifications_api_mutations(
    notifications_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify mark-read, mark-all-read, delete, preferences, and rebuild routes."""

    now = datetime.now(timezone.utc)
    called: list[str] = []

    async def fake_mark_read(_db, user_id: int, notif_id: int):
        called.append(f"read:{user_id}:{notif_id}")
        return SimpleNamespace(
            id=notif_id,
            user_id=user_id,
            type="lesson_reminder",
            title="درس اليوم",
            message="ابدأ الدرس الآن.",
            status="read",
            priority="normal",
            scheduled_for=now,
            delivered_at=now,
            read_at=now,
            action_url="/lessons/1",
            metadata_json={"source_type": "lesson", "source_id": "1"},
            created_at=now,
            updated_at=now,
        )

    async def fake_mark_all(_db, user_id: int):
        called.append(f"all:{user_id}")

    async def fake_delete(_db, user_id: int, notif_id: int):
        called.append(f"delete:{user_id}:{notif_id}")

    async def fake_get_preferences(_db, user_id: int):
        called.append(f"pref:{user_id}")
        return SimpleNamespace(
            id=3,
            user_id=user_id,
            exam_reminders_enabled=True,
            lesson_reminders_enabled=False,
            push_enabled=True,
            email_enabled=False,
            in_app_enabled=True,
            reminder_time_local="08:00",
            timezone="Asia/Damascus",
            created_at=now,
            updated_at=now,
        )

    async def fake_update_preferences(_db, user_id: int, updates: NotificationPreferenceUpdate):
        called.append(f"update-pref:{user_id}:{updates.lesson_reminders_enabled}")
        return await fake_get_preferences(_db, user_id)

    async def fake_rebuild(_db, user_id: int):
        called.append(f"rebuild:{user_id}")

    monkeypatch.setattr("app.services.notification_service.mark_read", fake_mark_read)
    monkeypatch.setattr("app.services.notification_service.mark_all_read", fake_mark_all)
    monkeypatch.setattr("app.services.notification_service.delete_notification", fake_delete)
    monkeypatch.setattr("app.services.notification_service.get_preferences", fake_get_preferences)
    monkeypatch.setattr("app.services.notification_service.update_preferences", fake_update_preferences)
    monkeypatch.setattr("app.services.notification_service.rebuild_reminders", fake_rebuild)

    assert notifications_client.patch("/api/v1/notifications/5/read").json()["status"] == "read"
    assert notifications_client.patch("/api/v1/notifications/mark-all-read").json() == {"status": "success"}
    assert notifications_client.delete("/api/v1/notifications/5").status_code == 204
    assert notifications_client.get("/api/v1/notification-preferences").json()["timezone"] == "Asia/Damascus"
    assert notifications_client.patch(
        "/api/v1/notification-preferences",
        json={"lesson_reminders_enabled": False},
    ).status_code == 200
    assert notifications_client.post("/api/v1/reminders/rebuild").json()["status"] == "success"

    assert "read:10:5" in called
    assert "all:10" in called
    assert "delete:10:5" in called
    assert "rebuild:10" in called


@patch("app.workers.notification_tasks.SessionLocal")
def test_celery_task_reminders_delivery(mock_session_cls: MagicMock) -> None:
    """Test that check_pending_reminders celery task processes and delivers events."""
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session

    # 1. Setup mock ReminderEvent, User preference, and duplicate check return values
    from app.models.notification import ReminderEvent, NotificationPreference
    
    event = ReminderEvent(
        id=1,
        user_id=10,
        source_type="exam",
        source_id="plan-1",
        reminder_type="7_days_before",
        scheduled_for=datetime.now(timezone.utc),
        status="pending"
    )
    pref = NotificationPreference(
        user_id=10,
        exam_reminders_enabled=True,
        lesson_reminders_enabled=True
    )

    mock_session.scalars.return_value.all.return_value = [event]
    mock_session.scalar.side_effect = [pref, None]  # First call for pref, second for duplicate check (None = no dup)

    # Assign mock ID when db.flush() is called
    def mock_flush():
        for call in mock_session.add.call_args_list:
            obj = call[0][0]
            if obj.__class__.__name__ == "Notification":
                obj.id = 42
    mock_session.flush.side_effect = mock_flush

    # 2. Run the Celery task
    result = check_pending_reminders()

    # 3. Assert results
    assert "Sent: 1" in result
    assert "Skipped: 0" in result
    assert event.status == "sent"
    assert event.notification_id is not None
    mock_session.add.assert_called()
    mock_session.commit.assert_called_once()


@patch("app.workers.notification_tasks.SessionLocal")
def test_celery_task_skipped_preferences(mock_session_cls: MagicMock) -> None:
    """Test that check_pending_reminders skips events when notifications are disabled by preferences."""
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session

    from app.models.notification import ReminderEvent, NotificationPreference

    event = ReminderEvent(
        id=1,
        user_id=10,
        source_type="lesson",
        source_id="1",
        reminder_type="1_day_before",
        scheduled_for=datetime.now(timezone.utc),
        status="pending"
    )
    # Preferences disabled for lesson reminders
    pref = NotificationPreference(
        user_id=10,
        exam_reminders_enabled=True,
        lesson_reminders_enabled=False
    )

    mock_session.scalars.return_value.all.return_value = [event]
    mock_session.scalar.return_value = pref

    result = check_pending_reminders()

    assert "Sent: 0" in result
    assert "Skipped: 1" in result
    assert event.status == "skipped"
    mock_session.commit.assert_called_once()


@patch("app.workers.notification_tasks.SessionLocal")
def test_celery_task_skips_when_in_app_notifications_disabled(mock_session_cls: MagicMock) -> None:
    """In-app disabled means pending reminders are skipped instead of delivered."""

    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session

    from app.models.notification import NotificationPreference, ReminderEvent

    event = ReminderEvent(
        id=1,
        user_id=10,
        source_type="exam",
        source_id="1",
        reminder_type="at_exam_time",
        scheduled_for=datetime.now(timezone.utc),
        status="pending",
    )
    pref = NotificationPreference(user_id=10, in_app_enabled=False)

    mock_session.scalars.return_value.all.return_value = [event]
    mock_session.scalar.return_value = pref

    result = check_pending_reminders()

    assert "Sent: 0" in result
    assert "Skipped: 1" in result
    assert event.status == "skipped"
    mock_session.commit.assert_called_once()


@patch("app.workers.notification_tasks.SessionLocal")
def test_celery_task_uses_existing_notification_for_duplicate(mock_session_cls: MagicMock) -> None:
    """Duplicate reminder delivery reuses the existing notification and does not insert another."""

    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session

    from app.models.notification import Notification, NotificationPreference, ReminderEvent

    scheduled_for = datetime.now(timezone.utc)
    event = ReminderEvent(
        id=1,
        user_id=10,
        source_type="lesson",
        source_id="1",
        reminder_type="30_minutes_before",
        scheduled_for=scheduled_for,
        status="pending",
    )
    pref = NotificationPreference(user_id=10, lesson_reminders_enabled=True, in_app_enabled=True)
    existing_notification = Notification(
        id=99,
        user_id=10,
        type="lesson_reminder",
        title="30 دقيقة على موعد الدرس",
        message="سيبدأ درسك بعد 30 دقيقة.",
        status="unread",
        priority="normal",
        scheduled_for=scheduled_for,
        action_url="/lessons/1",
    )

    mock_session.scalars.return_value.all.return_value = [event]
    mock_session.scalar.side_effect = [pref, existing_notification]

    result = check_pending_reminders()

    assert "Sent: 0" in result
    assert "Skipped: 1" in result
    assert event.status == "sent"
    assert event.notification_id == 99
    added_classes = [call.args[0].__class__.__name__ for call in mock_session.add.call_args_list]
    assert added_classes == ["ReminderEvent"]
    mock_session.commit.assert_called_once()
