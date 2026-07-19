"""Evidence-backed dashboard aggregates for the student home screen."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import QuizAttempt
from app.models.chemistry import Lesson, LessonProgress
from app.models.flashcard import FlashcardProgress
from app.models.notification import Notification
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.user import User
from app.schemas.dashboard import (
    DashboardActivePlanProgress,
    DashboardCurriculumProgress,
    DashboardDataQuality,
    DashboardFlashcardSummary,
    DashboardLessonSummary,
    DashboardNotificationSummary,
    DashboardPlanLessonSummary,
    DashboardPrimaryMission,
    DashboardQuizSummary,
    DashboardResponse,
    DashboardStudyPlanSummary,
    DashboardTopicSummary,
    WeakTopicsState,
)
from app.services.study_plan_service import get_study_plan_progress


DASHBOARD_SEMANTICS_VERSION = "dashboard-progress-v1"
WEAK_TOPIC_MIN_ANSWERS = 5
WEAK_TOPIC_ACCURACY_THRESHOLD = 70.0


def _today() -> date:
    return date.today()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _curriculum_progress(
    db: AsyncSession,
    user_id: int,
) -> DashboardCurriculumProgress:
    total = int(await db.scalar(select(func.count(Lesson.id))) or 0)
    completed = int(
        await db.scalar(
            select(func.count(distinct(LessonProgress.lesson_id)))
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.status == "completed",
            )
        )
        or 0
    )
    completed = min(completed, total)
    percent = round((completed / total) * 100) if total else None
    return DashboardCurriculumProgress(
        total_lessons=total,
        completed_lessons=completed,
        percent=percent,
    )


async def _has_lesson_progress(db: AsyncSession, user_id: int) -> bool:
    count = int(
        await db.scalar(
            select(func.count(LessonProgress.id)).where(LessonProgress.user_id == user_id)
        )
        or 0
    )
    return count > 0


async def _continue_lesson(db: AsyncSession, user_id: int) -> DashboardLessonSummary | None:
    completed_lesson_ids = select(LessonProgress.lesson_id).where(
        LessonProgress.user_id == user_id,
        LessonProgress.status == "completed",
    )
    progress_result = await db.execute(
        select(LessonProgress)
        .options(selectinload(LessonProgress.lesson).selectinload(Lesson.chapter))
        .where(
            LessonProgress.user_id == user_id,
            LessonProgress.status == "in_progress",
            LessonProgress.lesson_id.not_in(completed_lesson_ids),
        )
        .order_by(LessonProgress.created_at.desc(), LessonProgress.id.desc())
        .limit(1)
    )
    progress = progress_result.scalar_one_or_none()
    if progress and progress.lesson:
        lesson = progress.lesson
        return DashboardLessonSummary(
            id=lesson.id,
            title_ar=lesson.title_ar,
            chapter_id=lesson.chapter_id,
            chapter_title_ar=lesson.chapter.title_ar if lesson.chapter else None,
            progress_percent=None,
            progress=None,
            duration_min=lesson.duration_min,
            status="in_progress",
        )

    lesson_result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.chapter))
        .where(Lesson.id.not_in(completed_lesson_ids))
        .order_by(Lesson.chapter_id, Lesson.order, Lesson.id)
        .limit(1)
    )
    lesson = lesson_result.scalar_one_or_none()
    if lesson is None:
        return None
    return DashboardLessonSummary(
        id=lesson.id,
        title_ar=lesson.title_ar,
        chapter_id=lesson.chapter_id,
        chapter_title_ar=lesson.chapter.title_ar if lesson.chapter else None,
        progress_percent=None,
        progress=None,
        duration_min=lesson.duration_min,
        status="not_started",
    )


async def _weak_topics(
    db: AsyncSession,
    user_id: int,
) -> tuple[list[DashboardTopicSummary], WeakTopicsState, int]:
    result = await db.execute(
        select(QuizAttempt, Topic)
        .join(Topic, Topic.id == QuizAttempt.topic_id)
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
    )
    evidence: dict[int, dict[str, Any]] = {}
    total_answered = 0
    for attempt, topic in result.all():
        answered = max(int(attempt.total or 0), 0)
        if answered == 0:
            continue
        correct = min(max(int(attempt.score or 0), 0), answered)
        total_answered += answered
        record = evidence.setdefault(
            topic.id,
            {
                "topic": topic,
                "correct": 0,
                "answered": 0,
                "attempt_count": 0,
                "last_evidence_at": None,
            },
        )
        record["correct"] += correct
        record["answered"] += answered
        record["attempt_count"] += 1
        completed_at = attempt.completed_at
        if completed_at and (
            record["last_evidence_at"] is None
            or completed_at > record["last_evidence_at"]
        ):
            record["last_evidence_at"] = completed_at

    has_sufficient_evidence = any(
        int(record["answered"]) >= WEAK_TOPIC_MIN_ANSWERS for record in evidence.values()
    )
    weak_topics: list[DashboardTopicSummary] = []
    for record in evidence.values():
        answered = int(record["answered"])
        if answered < WEAK_TOPIC_MIN_ANSWERS:
            continue
        accuracy = round((int(record["correct"]) / answered) * 100, 1)
        if accuracy >= WEAK_TOPIC_ACCURACY_THRESHOLD:
            continue
        topic: Topic = record["topic"]
        weak_topics.append(
            DashboardTopicSummary(
                topic_id=topic.id,
                title_ar=topic.title_ar,
                accuracy_percent=accuracy,
                answered_questions=answered,
                attempt_count=int(record["attempt_count"]),
                last_evidence_at=record["last_evidence_at"],
                evidence_level="established" if answered >= 10 else "limited",
                reason="دقة إجاباتك في اختبارات هذا الموضوع أقل من 70٪.",
                action_url=f"/quiz?topicId={topic.id}",
                best_quiz_score=accuracy,
            )
        )

    weak_topics.sort(
        key=lambda item: (
            item.accuracy_percent,
            -(item.last_evidence_at.timestamp() if item.last_evidence_at else 0),
        )
    )
    state: WeakTopicsState = "ready" if has_sufficient_evidence else "insufficient_evidence"
    return weak_topics[:3], state, total_answered


def _flashcard_is_due(progress: FlashcardProgress, today: date) -> bool:
    if progress.mastered:
        return False
    if progress.due_at is not None:
        return progress.due_at.date() <= today
    return progress.next_review_at is None or progress.next_review_at <= today


async def _flashcards(db: AsyncSession, user_id: int) -> DashboardFlashcardSummary:
    today = _today()
    result = await db.execute(select(FlashcardProgress).where(FlashcardProgress.user_id == user_id))
    progress_rows = list(result.scalars().all())
    return DashboardFlashcardSummary(
        due_count=sum(1 for progress in progress_rows if _flashcard_is_due(progress, today)),
        mastered_count=sum(1 for progress in progress_rows if progress.mastered),
        total_reviewed=len(progress_rows),
    )


async def _latest_quiz(db: AsyncSession, user_id: int) -> DashboardQuizSummary | None:
    result = await db.execute(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.topic))
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()
    if attempt is None:
        return None
    return DashboardQuizSummary(
        title=f"راجع اختبار {attempt.topic.title_ar if attempt.topic else 'الكيمياء'}",
        topic_id=attempt.topic_id,
        score=attempt.score,
        total=attempt.total,
    )


def _plan_lesson(item: dict[str, Any] | None) -> DashboardPlanLessonSummary | None:
    if not item or item.get("lesson_id") is None:
        return None
    scheduled_date = item.get("scheduled_date")
    return DashboardPlanLessonSummary(
        id=int(item["lesson_id"]),
        title_ar=str(item.get("lesson_title_ar") or item.get("title_ar") or "درس الكيمياء"),
        scheduled_date=scheduled_date,
        status=str(item.get("status") or "not_started"),
        estimated_minutes=max(int(item.get("estimated_minutes") or 0), 0),
    )


async def _study_plan(
    db: AsyncSession,
    user_id: int,
) -> tuple[
    DashboardStudyPlanSummary | None,
    DashboardActivePlanProgress | None,
    list[dict[str, Any]],
]:
    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id, StudyPlan.status == "active")
        .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        return None, None, []

    days_to_exam = (plan.exam_date - _today()).days if plan.exam_date else None
    metadata = plan.plan_json if isinstance(plan.plan_json, dict) else {}
    summary = DashboardStudyPlanSummary(
        id=plan.id,
        exam_date=plan.exam_date,
        days_to_exam=days_to_exam,
        status=plan.status,
        metadata=metadata,
    )
    raw_progress = await get_study_plan_progress(db, plan.id, user_id)
    scheduled_lessons = [
        item for item in raw_progress.get("scheduled_lessons", []) if isinstance(item, dict)
    ]
    total = int(raw_progress.get("total_scheduled_lessons") or 0)
    if total == 0:
        return summary, None, []

    next_lesson_id = (raw_progress.get("next_lesson") or {}).get("id")
    next_lesson_item = next(
        (item for item in scheduled_lessons if item.get("lesson_id") == next_lesson_id),
        None,
    )
    progress = DashboardActivePlanProgress(
        plan_id=plan.id,
        total_scheduled_lessons=total,
        completed_lessons=int(raw_progress.get("completed_lessons") or 0),
        in_progress_lessons=int(raw_progress.get("in_progress_lessons") or 0),
        overdue_lessons=int(raw_progress.get("overdue_lessons") or 0),
        percent=round((int(raw_progress.get("completed_lessons") or 0) / total) * 100),
        next_lesson=_plan_lesson(next_lesson_item),
    )
    return summary, progress, scheduled_lessons


def _mission_for_lesson(
    *,
    kind: str,
    item: dict[str, Any],
    plan_id: int,
) -> DashboardPrimaryMission:
    lesson_id = int(item["lesson_id"])
    title = str(item.get("lesson_title_ar") or "درس الكيمياء")
    if kind == "overdue_lesson":
        return DashboardPrimaryMission(
            kind="overdue_lesson",
            title_ar="لديك درس متأخر",
            description_ar=f"{title} لم يكتمل بعد. ابدأ به لاستعادة مسار الخطة.",
            action_label_ar="ابدأ الدرس",
            action_url=f"/study-session/{lesson_id}?planId={plan_id}",
            reason_code="OLDEST_OVERDUE_PLAN_LESSON",
            lesson_id=lesson_id,
            study_plan_id=plan_id,
        )
    if kind == "today_lesson":
        return DashboardPrimaryMission(
            kind="today_lesson",
            title_ar="مهمة اليوم جاهزة",
            description_ar=f"حان وقت دراسة {title} ضمن خطتك الحالية.",
            action_label_ar="ابدأ مهمة اليوم",
            action_url=f"/study-session/{lesson_id}?planId={plan_id}",
            reason_code="TODAY_PLAN_LESSON",
            lesson_id=lesson_id,
            study_plan_id=plan_id,
        )
    return DashboardPrimaryMission(
        kind="next_lesson",
        title_ar="الدرس التالي في خطتك",
        description_ar=f"تابع مسارك ببدء {title}.",
        action_label_ar="ابدأ الدرس التالي",
        action_url=f"/study-session/{lesson_id}?planId={plan_id}",
        reason_code="NEXT_PLAN_LESSON",
        lesson_id=lesson_id,
        study_plan_id=plan_id,
    )


def _primary_mission(
    *,
    active_plan: DashboardActivePlanProgress | None,
    scheduled_lessons: list[dict[str, Any]],
    flashcards: DashboardFlashcardSummary,
    curriculum: DashboardCurriculumProgress,
) -> DashboardPrimaryMission:
    today = _today()
    if active_plan is not None:
        overdue = sorted(
            (item for item in scheduled_lessons if item.get("status") == "overdue"),
            key=lambda item: str(item.get("scheduled_date") or "9999-12-31"),
        )
        if overdue:
            return _mission_for_lesson(
                kind="overdue_lesson",
                item=overdue[0],
                plan_id=active_plan.plan_id,
            )

        today_items = [
            item
            for item in scheduled_lessons
            if item.get("scheduled_date") == today.isoformat()
            and item.get("status") in {"not_started", "in_progress"}
        ]
        if today_items:
            return _mission_for_lesson(
                kind="today_lesson",
                item=today_items[0],
                plan_id=active_plan.plan_id,
            )

    if flashcards.due_count > 0:
        return DashboardPrimaryMission(
            kind="due_flashcards",
            title_ar="بطاقات جاهزة للمراجعة",
            description_ar=f"لديك {flashcards.due_count} بطاقة مستحقة اليوم.",
            action_label_ar="راجع البطاقات",
            action_url="/flashcards",
            reason_code="DUE_FLASHCARDS_AVAILABLE",
            study_plan_id=active_plan.plan_id if active_plan else None,
        )

    if active_plan is not None and active_plan.next_lesson is not None:
        next_item = next(
            (
                item
                for item in scheduled_lessons
                if item.get("lesson_id") == active_plan.next_lesson.id
            ),
            None,
        )
        if next_item:
            return _mission_for_lesson(
                kind="next_lesson",
                item=next_item,
                plan_id=active_plan.plan_id,
            )

    if curriculum.total_lessons > 0:
        return DashboardPrimaryMission(
            kind="create_plan",
            title_ar="أنشئ مسارك الدراسي",
            description_ar="أنشئ خطة مرتبطة بدروس المنهج لتظهر مهمتك التالية بوضوح.",
            action_label_ar="إنشاء خطة دراسة",
            action_url="/study-plan",
            reason_code="NO_USABLE_ACTIVE_PLAN",
        )
    return DashboardPrimaryMission(
        kind="create_plan",
        title_ar="لا توجد دروس متاحة بعد",
        description_ar="لم يتم تحميل منهج الكيمياء في الخادم بعد.",
        action_label_ar="عرض الدروس",
        action_url="/lessons",
        reason_code="CURRICULUM_EMPTY",
    )


async def _unread_notifications(db: AsyncSession, user_id: int) -> DashboardNotificationSummary:
    count = int(
        await db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.status == "unread",
            )
        )
        or 0
    )
    return DashboardNotificationSummary(unread_count=count)


async def get_dashboard(db: AsyncSession, user_id: int) -> DashboardResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError("Current user was not found")

    curriculum = await _curriculum_progress(db, user_id)
    continue_lesson = await _continue_lesson(db, user_id)
    has_lesson_progress = await _has_lesson_progress(db, user_id)
    flashcards = await _flashcards(db, user_id)
    weak_topics, weak_topics_state, quiz_answer_count = await _weak_topics(db, user_id)
    next_quiz = await _latest_quiz(db, user_id)
    study_plan, active_plan, scheduled_lessons = await _study_plan(db, user_id)
    notifications = await _unread_notifications(db, user_id)
    mission = _primary_mission(
        active_plan=active_plan,
        scheduled_lessons=scheduled_lessons,
        flashcards=flashcards,
        curriculum=curriculum,
    )

    return DashboardResponse(
        semantics_version=DASHBOARD_SEMANTICS_VERSION,
        generated_at=_now(),
        user_id=user_id,
        student_name=user.name or user.first_name,
        xp=user.xp,
        level=user.level,
        streak_days=user.streak_days,
        curriculum_progress=curriculum,
        active_plan_progress=active_plan,
        primary_mission=mission,
        weak_topics_state=weak_topics_state,
        continue_lesson=continue_lesson,
        weak_topics=weak_topics,
        due_flashcards=flashcards,
        next_quiz=next_quiz,
        study_plan=study_plan,
        notifications=notifications,
        quick_tools=[
            {"label": "اسأل الذكاء", "route": "/ask-ai"},
            {"label": "حل موجه", "route": "/guided-lab"},
            {"label": "اختبار", "route": "/quiz"},
            {"label": "بطاقات", "route": "/flashcards"},
            {"label": "حل واجب", "route": "/homework"},
        ],
        data_quality=DashboardDataQuality(
            has_curriculum_data=curriculum.total_lessons > 0,
            has_lesson_progress=has_lesson_progress,
            has_active_study_plan=study_plan is not None,
            has_plan_items=active_plan is not None,
            has_quiz_evidence=quiz_answer_count > 0,
            has_weak_topic_evidence=weak_topics_state == "ready",
            weak_topic_answer_count=quiz_answer_count,
            weekly_xp_available=False,
        ),
        overall_progress=curriculum.percent,
        today_mission=mission.description_ar,
        current_streak=user.streak_days,
        lesson_progress_percentage=curriculum.percent,
        flashcards_due_count=flashcards.due_count,
        weekly_xp=None,
    )
