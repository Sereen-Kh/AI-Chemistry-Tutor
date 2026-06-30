"""Dashboard aggregate service for the student home screen."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import QuizAttempt
from app.models.chemistry import Lesson, LessonProgress
from app.models.flashcard import FlashcardProgress
from app.models.notification import Notification
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.user import User
from app.models.user_progress import UserProgress
from app.schemas.dashboard import (
    DashboardFlashcardSummary,
    DashboardLessonSummary,
    DashboardNotificationSummary,
    DashboardQuizSummary,
    DashboardResponse,
    DashboardStudyPlanSummary,
    DashboardTopicSummary,
)


async def _continue_lesson(db: AsyncSession, user_id: int) -> DashboardLessonSummary | None:
    progress_result = await db.execute(
        select(LessonProgress)
        .options(selectinload(LessonProgress.lesson).selectinload(Lesson.chapter))
        .where(LessonProgress.user_id == user_id, LessonProgress.status != "completed")
        .order_by(LessonProgress.created_at.desc())
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
            progress=50 if progress.status == "in_progress" else 0,
            duration_min=lesson.duration_min,
            status=progress.status,
        )

    lesson_result = await db.execute(
        select(Lesson).options(selectinload(Lesson.chapter)).order_by(Lesson.chapter_id, Lesson.order, Lesson.id).limit(1)
    )
    lesson = lesson_result.scalar_one_or_none()
    if lesson is None:
        return None
    return DashboardLessonSummary(
        id=lesson.id,
        title_ar=lesson.title_ar,
        chapter_id=lesson.chapter_id,
        chapter_title_ar=lesson.chapter.title_ar if lesson.chapter else None,
        progress=0,
        duration_min=lesson.duration_min,
        status="not_started",
    )


async def _overall_progress(db: AsyncSession, user_id: int) -> int:
    total = int(await db.scalar(select(func.count(Lesson.id))) or 0)
    if total == 0:
        return 0
    completed = int(
        await db.scalar(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.user_id == user_id,
                LessonProgress.status == "completed",
            )
        )
        or 0
    )
    return min(100, round((completed / total) * 100))


async def _weak_topics(db: AsyncSession, user_id: int) -> list[DashboardTopicSummary]:
    result = await db.execute(
        select(UserProgress, Topic)
        .join(Topic, Topic.id == UserProgress.topic_id)
        .where(UserProgress.user_id == user_id)
        .order_by(UserProgress.best_quiz_score.asc(), UserProgress.last_activity.desc())
        .limit(3)
    )
    topics = [
        DashboardTopicSummary(
            topic_id=topic.id,
            title_ar=topic.title_ar,
            best_quiz_score=progress.best_quiz_score,
            reason="نتيجة الاختبارات في هذا الموضوع تحتاج مراجعة.",
        )
        for progress, topic in result.all()
        if progress.best_quiz_score < 70
    ]
    if topics:
        return topics

    fallback = await db.execute(select(Topic).order_by(Topic.difficulty.desc(), Topic.order).limit(3))
    return [
        DashboardTopicSummary(
            topic_id=topic.id,
            title_ar=topic.title_ar,
            best_quiz_score=0,
            reason="موضوع مقترح للتدريب.",
        )
        for topic in fallback.scalars().all()
    ]


async def _flashcards(db: AsyncSession, user_id: int) -> DashboardFlashcardSummary:
    today = date.today()
    result = await db.execute(select(FlashcardProgress).where(FlashcardProgress.user_id == user_id))
    progress_rows = list(result.scalars().all())
    due_count = sum(
        1
        for progress in progress_rows
        if not progress.mastered or progress.next_review_at is None or progress.next_review_at <= today
    )
    return DashboardFlashcardSummary(
        due_count=due_count,
        mastered_count=sum(1 for progress in progress_rows if progress.mastered),
        total_reviewed=len(progress_rows),
    )


async def _latest_quiz(db: AsyncSession, user_id: int) -> DashboardQuizSummary | None:
    result = await db.execute(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.topic))
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()
    if attempt:
        return DashboardQuizSummary(
            title=f"راجع اختبار {attempt.topic.title_ar if attempt.topic else 'الكيمياء'}",
            topic_id=attempt.topic_id,
            score=attempt.score,
            total=attempt.total,
        )
    topic = await db.scalar(select(Topic).order_by(Topic.order).limit(1))
    if topic is None:
        return None
    return DashboardQuizSummary(title=f"اختبار قصير: {topic.title_ar}", topic_id=topic.id)


async def _study_plan(db: AsyncSession, user_id: int) -> DashboardStudyPlanSummary | None:
    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id, StudyPlan.status == "active")
        .order_by(StudyPlan.created_at.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        return None
    days_to_exam = (plan.exam_date - date.today()).days if plan.exam_date else None
    metadata = plan.plan_json if isinstance(plan.plan_json, dict) else {}
    return DashboardStudyPlanSummary(
        id=plan.id,
        exam_date=plan.exam_date,
        days_to_exam=days_to_exam,
        status=plan.status,
        metadata=metadata,
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

    continue_lesson = await _continue_lesson(db, user_id)
    overall = await _overall_progress(db, user_id)
    flashcards = await _flashcards(db, user_id)
    weak_topics = await _weak_topics(db, user_id)
    next_quiz = await _latest_quiz(db, user_id)
    study_plan = await _study_plan(db, user_id)
    notifications = await _unread_notifications(db, user_id)

    return DashboardResponse(
        user_id=user_id,
        student_name=user.name or user.first_name,
        xp=user.xp,
        level=user.level,
        streak_days=user.streak_days,
        overall_progress=overall,
        today_mission="أكمل درساً قصيراً، ثم حل مسألة واحدة خطوة بخطوة.",
        continue_lesson=continue_lesson,
        weak_topics=weak_topics,
        due_flashcards=flashcards,
        next_quiz=next_quiz,
        study_plan=study_plan,
        notifications=notifications,
        quick_tools=[
            {"label": "اسأل الذكاء", "route": "/ask-ai"},
            {"label": "حل موجه", "route": "/guided-lab"},
            {"label": "اختبار", "route": "/quizzes"},
            {"label": "بطاقات", "route": "/flashcards"},
            {"label": "حل واجب", "route": "/homework"},
        ],
        data_quality={
            "has_real_lesson_progress": continue_lesson is not None,
            "has_active_study_plan": study_plan is not None,
            "has_flashcard_progress": flashcards.total_reviewed > 0,
        },
        # Flat accessors for frontend parity.
        current_streak=user.streak_days,
        lesson_progress_percentage=overall,
        flashcards_due_count=flashcards.due_count,
        weekly_xp=user.xp,
    )
