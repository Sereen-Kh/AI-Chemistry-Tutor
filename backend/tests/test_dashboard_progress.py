"""Deterministic tests for dashboard-progress-v1 semantics."""

import asyncio
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.assessment import QuizAttempt
from app.models.chemistry import Chapter, Lesson, LessonProgress, Unit
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.user import User
from app.schemas.dashboard import (
    DashboardActivePlanProgress,
    DashboardCurriculumProgress,
    DashboardFlashcardSummary,
    DashboardPlanLessonSummary,
)
from app.services import dashboard_service


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture()
def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def init() -> async_sessionmaker[AsyncSession]:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    factory = run_async(init())
    yield factory
    run_async(engine.dispose())


async def _user(db: AsyncSession, suffix: str = "one") -> User:
    user = User(
        first_name="سارة",
        last_name="",
        email=f"dashboard-{suffix}@example.com",
        hashed_password="hashed",
    )
    db.add(user)
    await db.flush()
    return user


async def _lessons(db: AsyncSession, count: int) -> list[Lesson]:
    unit = Unit(unit_number=1, semester=1, title_ar="الوحدة الأولى", order=1)
    db.add(unit)
    await db.flush()
    chapter = Chapter(unit_id=unit.id, title_ar="الفصل الأول", order=1)
    db.add(chapter)
    await db.flush()
    lessons = [
        Lesson(
            chapter_id=chapter.id,
            title_ar=f"الدرس {index}",
            order=index,
            duration_min=45,
        )
        for index in range(1, count + 1)
    ]
    db.add_all(lessons)
    await db.flush()
    return lessons


def _schedule_item(day: date, lesson: Lesson) -> dict:
    return {
        "date": day.isoformat(),
        "sessions": [
            {
                "type": "lesson",
                "lesson_id": lesson.id,
                "title": lesson.title_ar,
                "minutes": lesson.duration_min,
                "status": "planned",
                "completed": False,
            }
        ],
    }


def test_curriculum_progress_counts_distinct_completed_lessons(session_factory) -> None:
    async def scenario():
        async with session_factory() as db:
            user = await _user(db)
            lessons = await _lessons(db, 9)
            db.add_all(
                [
                    LessonProgress(user_id=user.id, lesson_id=lessons[0].id, status="completed"),
                    LessonProgress(user_id=user.id, lesson_id=lessons[0].id, status="completed"),
                    LessonProgress(user_id=user.id, lesson_id=lessons[1].id, status="completed"),
                    LessonProgress(user_id=user.id, lesson_id=lessons[2].id, status="completed"),
                    LessonProgress(user_id=user.id, lesson_id=lessons[3].id, status="in_progress"),
                ]
            )
            await db.commit()

            progress = await dashboard_service._curriculum_progress(db, user.id)
            current = await dashboard_service._continue_lesson(db, user.id)

            assert progress.total_lessons == 9
            assert progress.completed_lessons == 3
            assert progress.percent == 33
            assert current is not None
            assert current.status == "in_progress"
            assert current.progress_percent is None
            assert current.progress is None

    run_async(scenario())


def test_empty_curriculum_and_empty_plan_return_null_progress(session_factory) -> None:
    async def scenario():
        async with session_factory() as db:
            user = await _user(db)
            db.add(StudyPlan(user_id=user.id, status="active", plan_json={"schedule": []}))
            await db.commit()

            curriculum = await dashboard_service._curriculum_progress(db, user.id)
            _summary, active_plan, scheduled = await dashboard_service._study_plan(db, user.id)

            assert curriculum.total_lessons == 0
            assert curriculum.percent is None
            assert active_plan is None
            assert scheduled == []

    run_async(scenario())


def test_active_plan_three_of_eight_is_thirty_eight_percent(
    session_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_today = date(2026, 7, 19)
    monkeypatch.setattr(dashboard_service, "_today", lambda: fixed_today)

    async def scenario():
        async with session_factory() as db:
            user = await _user(db)
            lessons = await _lessons(db, 8)
            schedule = [
                _schedule_item(fixed_today + timedelta(days=index), lesson)
                for index, lesson in enumerate(lessons)
            ]
            plan = StudyPlan(
                user_id=user.id,
                status="active",
                plan_json={
                    "title": "خطة الاختبار",
                    "schedule": schedule,
                    "completed_lesson_ids": [lesson.id for lesson in lessons[:3]],
                },
            )
            db.add(plan)
            await db.commit()

            _summary, progress, scheduled = await dashboard_service._study_plan(db, user.id)

            assert progress is not None
            assert progress.total_scheduled_lessons == 8
            assert progress.completed_lessons == 3
            assert progress.percent == 38
            assert len(scheduled) == 8

    run_async(scenario())


@pytest.mark.parametrize(
    ("score", "total", "expected_state", "expected_weak_count"),
    [
        (2, 4, "insufficient_evidence", 0),
        (3, 5, "ready", 1),
        (4, 5, "ready", 0),
    ],
)
def test_weak_topics_require_quiz_evidence(
    session_factory,
    score: int,
    total: int,
    expected_state: str,
    expected_weak_count: int,
) -> None:
    async def scenario():
        async with session_factory() as db:
            user = await _user(db)
            topic = Topic(title_ar="المحاليل", difficulty=5, order=1)
            db.add(topic)
            await db.flush()
            db.add(
                QuizAttempt(
                    user_id=user.id,
                    topic_id=topic.id,
                    score=score,
                    total=total,
                    completed_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
                )
            )
            await db.commit()

            weak_topics, state, answer_count = await dashboard_service._weak_topics(db, user.id)

            assert state == expected_state
            assert len(weak_topics) == expected_weak_count
            assert answer_count == total
            if weak_topics:
                assert weak_topics[0].accuracy_percent == 60
                assert weak_topics[0].answered_questions == 5
                assert weak_topics[0].evidence_level == "limited"

    run_async(scenario())


def test_no_quiz_evidence_never_uses_topic_difficulty(session_factory) -> None:
    async def scenario():
        async with session_factory() as db:
            user = await _user(db)
            db.add_all(
                [
                    Topic(title_ar="موضوع صعب", difficulty=5, order=1),
                    Topic(title_ar="موضوع آخر", difficulty=4, order=2),
                ]
            )
            await db.commit()

            weak_topics, state, answer_count = await dashboard_service._weak_topics(db, user.id)

            assert weak_topics == []
            assert state == "insufficient_evidence"
            assert answer_count == 0

    run_async(scenario())


def test_mission_priority_is_plan_then_flashcards_then_create_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_today = date(2026, 7, 19)
    monkeypatch.setattr(dashboard_service, "_today", lambda: fixed_today)
    next_lesson = DashboardPlanLessonSummary(
        id=3,
        title_ar="الدرس التالي",
        scheduled_date=fixed_today + timedelta(days=1),
        status="not_started",
        estimated_minutes=45,
    )
    active_plan = DashboardActivePlanProgress(
        plan_id=7,
        total_scheduled_lessons=3,
        completed_lessons=0,
        in_progress_lessons=0,
        overdue_lessons=1,
        percent=0,
        next_lesson=next_lesson,
    )
    curriculum = DashboardCurriculumProgress(total_lessons=9, completed_lessons=0, percent=0)
    due_cards = DashboardFlashcardSummary(due_count=4)
    scheduled = [
        {
            "lesson_id": 1,
            "lesson_title_ar": "درس متأخر",
            "scheduled_date": (fixed_today - timedelta(days=2)).isoformat(),
            "status": "overdue",
        },
        {
            "lesson_id": 2,
            "lesson_title_ar": "درس اليوم",
            "scheduled_date": fixed_today.isoformat(),
            "status": "not_started",
        },
        {
            "lesson_id": 3,
            "lesson_title_ar": "الدرس التالي",
            "scheduled_date": (fixed_today + timedelta(days=1)).isoformat(),
            "status": "not_started",
        },
    ]

    mission = dashboard_service._primary_mission(
        active_plan=active_plan,
        scheduled_lessons=scheduled,
        flashcards=due_cards,
        curriculum=curriculum,
    )
    assert mission.kind == "overdue_lesson"

    mission = dashboard_service._primary_mission(
        active_plan=active_plan,
        scheduled_lessons=scheduled[1:],
        flashcards=due_cards,
        curriculum=curriculum,
    )
    assert mission.kind == "today_lesson"

    mission = dashboard_service._primary_mission(
        active_plan=active_plan,
        scheduled_lessons=scheduled[2:],
        flashcards=due_cards,
        curriculum=curriculum,
    )
    assert mission.kind == "due_flashcards"

    mission = dashboard_service._primary_mission(
        active_plan=active_plan,
        scheduled_lessons=scheduled[2:],
        flashcards=DashboardFlashcardSummary(due_count=0),
        curriculum=curriculum,
    )
    assert mission.kind == "next_lesson"

    mission = dashboard_service._primary_mission(
        active_plan=None,
        scheduled_lessons=[],
        flashcards=DashboardFlashcardSummary(due_count=0),
        curriculum=curriculum,
    )
    assert mission.kind == "create_plan"


def test_dashboard_evidence_is_scoped_to_current_student(session_factory) -> None:
    async def scenario():
        async with session_factory() as db:
            owner = await _user(db, "owner")
            other = await _user(db, "other")
            lessons = await _lessons(db, 1)
            topic = Topic(title_ar="التركيز", difficulty=3, order=1)
            db.add(topic)
            await db.flush()
            db.add_all(
                [
                    LessonProgress(
                        user_id=other.id,
                        lesson_id=lessons[0].id,
                        status="completed",
                    ),
                    QuizAttempt(
                        user_id=other.id,
                        topic_id=topic.id,
                        score=1,
                        total=5,
                    ),
                ]
            )
            await db.commit()

            curriculum = await dashboard_service._curriculum_progress(db, owner.id)
            weak_topics, state, count = await dashboard_service._weak_topics(db, owner.id)

            assert curriculum.completed_lessons == 0
            assert weak_topics == []
            assert state == "insufficient_evidence"
            assert count == 0

    run_async(scenario())
