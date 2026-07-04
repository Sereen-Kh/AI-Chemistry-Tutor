import asyncio
from collections.abc import AsyncIterator
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.chemistry import LessonProgress
from app.models.study_plan import StudyPlan
from app.models.user import User
from app.schemas.study_plans import StudyPlanGenerateRequest
from app.services import study_plan_service


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture()
def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def init() -> async_sessionmaker[AsyncSession]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    factory = run_async(init())
    yield factory
    run_async(engine.dispose())


def _lesson(lesson_id: int, title: str, duration: int = 45) -> SimpleNamespace:
    unit = SimpleNamespace(id=1, unit_number=1, title_ar="الكيمياء اللاعضوية")
    chapter = SimpleNamespace(unit=unit, title_ar="المحاليل")
    return SimpleNamespace(
        id=lesson_id,
        title_ar=title,
        chapter_id=1,
        chapter=chapter,
        duration_min=duration,
    )


def test_study_plan_rejects_start_date_before_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(study_plan_service, "_today", lambda: date(2026, 6, 21))
    request = StudyPlanGenerateRequest(startDate="2025-09-01", endDate="2026-10-01", lessonIds=[1])

    with pytest.raises(HTTPException) as exc_info:
        study_plan_service._validate_plan_dates(request)

    assert exc_info.value.status_code == 422


def test_study_plan_accepts_current_or_future_start_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(study_plan_service, "_today", lambda: date(2026, 6, 21))
    request = StudyPlanGenerateRequest(startDate="2026-06-21", endDate="2026-07-01", lessonIds=[1])

    start_date, end_date, exam_date = study_plan_service._validate_plan_dates(request)

    assert start_date == date(2026, 6, 21)
    assert end_date == date(2026, 7, 1)
    assert exam_date is None


def test_study_plan_rejects_empty_lesson_selection() -> None:
    request = StudyPlanGenerateRequest(lessonIds=[])

    with pytest.raises(HTTPException) as exc_info:
        study_plan_service._lesson_ids(request.lessonIds)

    assert exc_info.value.status_code == 422
    assert "at least one selected lesson" in str(exc_info.value.detail)


def test_study_plan_rejects_invalid_lesson_ids() -> None:
    request = StudyPlanGenerateRequest(lessonIds=["abc", 0, -5])

    with pytest.raises(HTTPException) as exc_info:
        study_plan_service._lesson_ids(request.lessonIds)

    assert exc_info.value.status_code == 422
    assert "valid positive lesson IDs" in str(exc_info.value.detail)


def test_study_plan_normalizes_arabic_short_weekdays() -> None:
    days = study_plan_service._normalize_study_days(["ج", "س", "ح", "ن"], use_exam_defaults=False)

    assert days == ["fri", "sat", "sun", "mon"]


def test_study_plan_schedule_uses_selected_days_and_hours() -> None:
    start_date = date(2026, 6, 21)
    end_date = date(2026, 6, 29)
    study_days = ["fri", "sat", "sun", "mon"]
    hours = {day: 2 for day in study_days}

    schedule, summary = study_plan_service._build_schedule(
        lessons=[_lesson(1, "المحاليل المائية"), _lesson(2, "المحاليل الحمضية")],
        start_date=start_date,
        end_date=end_date,
        study_days=study_days,
        hours=hours,
    )

    assert schedule
    assert {entry["weekday"] for entry in schedule}.issubset(set(study_days))
    assert all(entry["date"] >= start_date.isoformat() for entry in schedule)
    assert summary["hours_by_day"] == hours
    assert summary["total_study_days"] == len(schedule)
    assert any(session["type"] == "lesson" for entry in schedule for session in entry["sessions"])
    assert all(
        session["type"] in {"lesson", "review"}
        for entry in schedule
        for session in entry["sessions"]
    )


def test_study_plan_builds_week_day_task_contract() -> None:
    schedule = [
        _schedule_entry("2026-06-22", 1, "درس 1"),
        _schedule_entry("2026-06-23", 2, "درس 2"),
    ]

    weeks = study_plan_service._build_plan_weeks(schedule)
    plan_json = {
        "overview": "خطة اختبار",
        "target_date": "2026-06-30",
        "weeks": weeks,
        "weak_topics": [],
        "recommendations": [],
    }

    study_plan_service._validate_plan_json_contract(plan_json)
    assert weeks[0]["week_number"] == 1
    assert weeks[0]["days"][0]["date"] == "2026-06-22"
    assert weeks[0]["days"][0]["lesson_ids"] == [1]
    task_types = {task["type"] for day in weeks[0]["days"] for task in day["tasks"]}
    assert "lesson" in task_types
    assert "flashcards" in task_types
    assert all(task["status"] in {"pending", "completed", "skipped"} for day in weeks[0]["days"] for task in day["tasks"])


def _plan_with_schedule(schedule: list[dict], completed_ids: list[int] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=10,
        plan_json={
            "title": "خطة الكيمياء",
            "completed_lesson_ids": completed_ids or [],
            "schedule": schedule,
            "summary": {"start_date": "2026-06-20", "end_date": "2026-06-30"},
        },
    )


def _schedule_entry(value: str, lesson_id: int, title: str, completed: bool = False) -> dict:
    return {
        "date": value,
        "weekday": "mon",
        "weekday_ar": "الاثنين",
        "planned_hours": 1,
        "planned_minutes": 60,
        "sessions": [
            {
                "type": "lesson",
                "lesson_id": lesson_id,
                "title": title,
                "minutes": 45,
                "status": "completed" if completed else "planned",
                "completed": completed,
            }
        ],
    }


def test_study_plan_progress_handles_empty_schedule() -> None:
    result = study_plan_service._build_study_plan_progress(
        plan=_plan_with_schedule([]),
        lessons_by_id={},
        progress_by_lesson_id={},
        today=date(2026, 6, 23),
    )

    assert result["total_scheduled_lessons"] == 0
    assert result["completion_percent"] == 0
    assert result["next_lesson"] is None


def test_study_plan_progress_counts_only_scheduled_lessons() -> None:
    schedule = [
        _schedule_entry("2026-06-20", 1, "درس 1", completed=True),
        _schedule_entry("2026-06-21", 2, "درس 2", completed=True),
        _schedule_entry("2026-06-22", 3, "درس 3", completed=True),
        _schedule_entry("2026-06-23", 4, "درس 4"),
        _schedule_entry("2026-06-24", 5, "درس 5"),
        _schedule_entry("2026-06-25", 6, "درس 6"),
        _schedule_entry("2026-06-26", 7, "درس 7"),
        _schedule_entry("2026-06-20", 8, "درس 8"),
    ]
    lessons_by_id = {lesson_id: _lesson(lesson_id, f"درس {lesson_id}") for lesson_id in range(1, 10)}

    result = study_plan_service._build_study_plan_progress(
        plan=_plan_with_schedule(schedule),
        lessons_by_id=lessons_by_id,
        progress_by_lesson_id={4: SimpleNamespace(status="in_progress")},
        today=date(2026, 6, 23),
    )

    assert result["total_scheduled_lessons"] == 8
    assert result["completed_lessons"] == 3
    assert result["in_progress_lessons"] == 1
    assert result["not_started_lessons"] == 3
    assert result["overdue_lessons"] == 1
    assert result["completion_percent"] == 37.5
    assert len(result["scheduled_lessons"]) == 8
    assert all(item["lesson_id"] != 9 for item in result["scheduled_lessons"])
    assert result["unit_progress"][0]["total_lessons"] == 8
    assert result["unit_progress"][0]["completed_lessons"] == 3


def test_study_plan_progress_detects_overdue_lessons() -> None:
    result = study_plan_service._build_study_plan_progress(
        plan=_plan_with_schedule([_schedule_entry("2026-06-20", 1, "درس قديم")]),
        lessons_by_id={1: _lesson(1, "درس قديم")},
        progress_by_lesson_id={},
        today=date(2026, 6, 23),
    )

    assert result["overdue_lessons"] == 1
    assert result["scheduled_lessons"][0]["status"] == "overdue"
    assert result["track_status"] == "behind"


def test_study_plan_progress_handles_all_completed() -> None:
    result = study_plan_service._build_study_plan_progress(
        plan=_plan_with_schedule(
            [
                _schedule_entry("2026-06-20", 1, "درس 1"),
                _schedule_entry("2026-06-21", 2, "درس 2"),
            ],
            completed_ids=[1, 2],
        ),
        lessons_by_id={1: _lesson(1, "درس 1"), 2: _lesson(2, "درس 2")},
        progress_by_lesson_id={},
        today=date(2026, 6, 23),
    )

    assert result["completed_lessons"] == 2
    assert result["completion_percent"] == 100
    assert result["track_status"] == "ahead"
    assert result["next_lesson"] is None


def test_complete_study_plan_lesson_rejects_lesson_outside_plan(session_factory) -> None:
    async def scenario():
        async with session_factory() as db:
            user = User(first_name="سارة", email="study-plan@example.com", hashed_password="hashed")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            plan = StudyPlan(
                user_id=user.id,
                status="active",
                plan_json={
                    "schedule": [_schedule_entry("2026-06-22", 1, "درس 1")],
                    "chapters": [],
                    "completed_lesson_ids": [],
                    "weeks": study_plan_service._build_plan_weeks([_schedule_entry("2026-06-22", 1, "درس 1")]),
                },
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)

            with pytest.raises(HTTPException) as exc_info:
                await study_plan_service.complete_study_plan_lesson(db, plan.id, user.id, 2)

            assert exc_info.value.status_code == 422

    run_async(scenario())


def test_complete_study_plan_lesson_updates_tasks_and_lesson_progress(session_factory) -> None:
    async def scenario():
        async with session_factory() as db:
            user = User(first_name="سارة", email="study-plan-complete@example.com", hashed_password="hashed")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            schedule = [_schedule_entry("2026-06-22", 1, "درس 1")]
            plan = StudyPlan(
                user_id=user.id,
                status="active",
                plan_json={
                    "schedule": schedule,
                    "chapters": [{"id": 1, "title": "فصل", "lessons": [{"id": 1, "title": "درس 1", "status": "current"}]}],
                    "completed_lesson_ids": [],
                    "weeks": study_plan_service._build_plan_weeks(schedule),
                    "summary": {"start_date": "2026-06-22", "end_date": "2026-06-30"},
                },
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)

            updated = await study_plan_service.complete_study_plan_lesson(db, plan.id, user.id, 1)
            metadata = updated.plan_json
            lesson_task = metadata["weeks"][0]["days"][0]["tasks"][0]

            assert metadata["completed_lesson_ids"] == [1]
            assert metadata["schedule"][0]["sessions"][0]["status"] == "completed"
            assert lesson_task["status"] == "completed"
            assert lesson_task["completed_at"]

            progress = await db.scalar(
                select(LessonProgress).where(LessonProgress.user_id == user.id, LessonProgress.lesson_id == 1)
            )
            assert progress is not None
            assert progress.status == "completed"
            assert isinstance(progress.completed_at, datetime)
            assert progress.completed_at.tzinfo is not None or progress.completed_at.replace(tzinfo=timezone.utc)

    run_async(scenario())
