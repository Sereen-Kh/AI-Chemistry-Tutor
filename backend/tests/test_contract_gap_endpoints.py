"""Regression tests for frontend/backend contract gap endpoints."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.main import app
from app.schemas.dashboard import DashboardResponse


@pytest.fixture()
def contract_client():
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


def test_dashboard_endpoint_returns_aggregate(contract_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_dashboard(_db, user_id: int):
        assert user_id == 10
        return DashboardResponse(
            user_id=10,
            student_name="سارة",
            xp=120,
            level=2,
            streak_days=4,
            overall_progress=35,
            today_mission="راجع درس التركيز.",
            weak_topics=[],
            quick_tools=[{"label": "حل موجه", "route": "/guided-lab"}],
        )

    monkeypatch.setattr("app.api.dashboard.get_dashboard", fake_dashboard)

    response = contract_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["student_name"] == "سارة"
    assert payload["overall_progress"] == 35
    assert payload["quick_tools"][0]["route"] == "/guided-lab"


def test_device_token_endpoints(contract_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    called: list[str] = []

    async def fake_register(_db, user_id: int, request):
        called.append(f"register:{user_id}:{request.platform}")
        return SimpleNamespace(
            id=1,
            user_id=user_id,
            token=request.token,
            platform=request.platform,
            created_at=now,
            updated_at=now,
        )

    async def fake_list(_db, user_id: int):
        called.append(f"list:{user_id}")
        return [
            SimpleNamespace(
                id=1,
                user_id=user_id,
                token="token-123456",
                platform="web",
                created_at=now,
                updated_at=now,
            )
        ]

    async def fake_delete(_db, user_id: int, token: str):
        called.append(f"delete:{user_id}:{token}")

    monkeypatch.setattr("app.services.device_service.register_device_token", fake_register)
    monkeypatch.setattr("app.services.device_service.list_device_tokens", fake_list)
    monkeypatch.setattr("app.services.device_service.delete_device_token", fake_delete)

    register_response = contract_client.post(
        "/api/v1/devices/register",
        json={"token": "token-123456", "platform": "web"},
    )
    assert register_response.status_code == 201
    assert register_response.json()["platform"] == "web"

    assert contract_client.get("/api/v1/devices").json()[0]["token"] == "token-123456"
    assert contract_client.delete("/api/v1/devices/token-123456").status_code == 204
    assert "register:10:web" in called
    assert "list:10" in called
    assert "delete:10:token-123456" in called


def test_homework_upload_accepts_multipart(
    contract_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    class FakeDb:
        def add(self, item):
            self.item = item

        async def commit(self):
            return None

        async def refresh(self, item):
            item.id = 77

    async def fake_db():
        yield FakeDb()

    app.dependency_overrides[get_async_db] = fake_db
    monkeypatch.setattr("app.api.homework.PROJECT_DIR", tmp_path)

    response = contract_client.post(
        "/api/v1/homework/upload",
        files={"file": ("homework.png", b"\x89PNG\r\n\x1a\nfake", "image/png")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["homework_id"] == 77
    assert payload["image_url"].startswith("/media/uploads/homework/10/")
    assert (tmp_path / "data" / "uploads" / "homework" / "10").exists()


def test_flashcard_generate_and_due_routes(contract_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    card = SimpleNamespace(
        id=5,
        topic_id=1,
        front_ar="ما هو الحمض؟",
        back_ar="مادة تعطي +H في الماء.",
        created_by="generated",
        created_at=now,
        updated_at=now,
    )

    async def fake_generate(_db, request):
        assert request.limit == 3
        return [card]

    async def fake_due(_db, user_id: int, limit: int):
        assert user_id == 10
        assert limit == 3
        return [(card, None)]

    monkeypatch.setattr("app.services.flashcard_service.generate_flashcards", fake_generate)
    monkeypatch.setattr("app.services.flashcard_service.due_flashcards", fake_due)

    generated = contract_client.post("/api/v1/flashcards/generate", json={"topic_id": 1, "limit": 3})
    assert generated.status_code == 201
    assert generated.json()[0]["created_by"] == "generated"

    due = contract_client.get("/api/v1/flashcards/due?limit=3")
    assert due.status_code == 200
    assert due.json()[0]["mastered"] is False


def test_study_plan_generation_and_complete_routes(contract_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    plan = SimpleNamespace(
        id=9,
        user_id=10,
        exam_date=date(2026, 6, 30),
        plan_json={"chapters": [], "weakTopics": [], "currentLesson": None},
        status="active",
        created_at=now,
        updated_at=now,
    )

    async def fake_generate(_db, user_id: int, request):
        assert user_id == 10
        assert request.lessonIds == [1, "2"]
        return plan

    async def fake_complete(_db, plan_id: int, user_id: int, lesson_id: int):
        assert (plan_id, user_id, lesson_id) == (9, 10, 2)
        return plan

    monkeypatch.setattr("app.services.study_plan_service.generate_study_plan", fake_generate)
    monkeypatch.setattr("app.services.study_plan_service.complete_study_plan_lesson", fake_complete)

    generated = contract_client.post("/api/v1/study-plans/generate", json={"lessonIds": [1, "2"]})
    assert generated.status_code == 201
    assert generated.json()["id"] == 9

    completed = contract_client.post("/api/v1/study-plans/9/lessons/2/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "active"
