"""Service for managing notifications, preferences, and reminder generation."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chemistry import Lesson, LessonProgress
from app.models.flashcard import Flashcard, FlashcardProgress
from app.models.notification import Notification, NotificationPreference, ReminderEvent
from app.models.study_plan import StudyPlan
from app.models.topic import Topic
from app.models.user_progress import UserProgress
from app.schemas.notification import NotificationCreate, NotificationPreferenceUpdate
from app.services import notification_delivery_service


NOTIFICATION_TYPES = {
    "study_reminder",
    "quiz_due",
    "homework_feedback",
    "streak_warning",
    "achievement_unlocked",
    "exam_countdown",
    "overdue_lesson",
    "flashcards_due",
    "quiz_reminder",
    "weak_topic",
    "system",
    # Legacy names accepted while existing clients migrate.
    "exam_reminder",
    "lesson_reminder",
    "quiz_reminder",
}


async def get_notifications(
    db: AsyncSession,
    user_id: int,
    *,
    status: str | None = None,
    type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    """Retrieve notifications for a user, sorted by newest first."""

    stmt = select(Notification).where(Notification.user_id == user_id)
    if status:
        stmt = stmt.where(Notification.status == status)
    if type:
        stmt = stmt.where(Notification.type == type)
    stmt = stmt.order_by(Notification.scheduled_for.desc(), Notification.id.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    stmt = select(func.count(Notification.id)).where(
        and_(Notification.user_id == user_id, Notification.status == "unread")
    )
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def mark_read(db: AsyncSession, user_id: int, notif_id: int) -> Notification:
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.status != "read":
        notif.status = "read"
        notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return notif


async def mark_all_read(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(
        select(Notification).where(and_(Notification.user_id == user_id, Notification.status == "unread"))
    )
    now = datetime.now(timezone.utc)
    for notif in result.scalars().all():
        notif.status = "read"
        notif.read_at = now
    await db.commit()


async def delete_notification(db: AsyncSession, user_id: int, notif_id: int) -> None:
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    await db.commit()


async def get_preferences(db: AsyncSession, user_id: int) -> NotificationPreference:
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    _sync_legacy_preference_fields(pref)
    return pref


async def update_preferences(
    db: AsyncSession, user_id: int, updates: NotificationPreferenceUpdate
) -> NotificationPreference:
    pref = await get_preferences(db, user_id)
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pref, key, value)

    # Keep legacy and new fields aligned.
    if "lesson_reminders_enabled" in update_data and "daily_study_reminder_enabled" not in update_data:
        pref.daily_study_reminder_enabled = bool(update_data["lesson_reminders_enabled"])
        pref.overdue_lesson_reminder_enabled = bool(update_data["lesson_reminders_enabled"])
    if "daily_study_reminder_enabled" in update_data and "lesson_reminders_enabled" not in update_data:
        pref.lesson_reminders_enabled = bool(update_data["daily_study_reminder_enabled"])
    if "exam_reminders_enabled" in update_data and "exam_reminder_enabled" not in update_data:
        pref.exam_reminder_enabled = bool(update_data["exam_reminders_enabled"])
    if "exam_reminder_enabled" in update_data and "exam_reminders_enabled" not in update_data:
        pref.exam_reminders_enabled = bool(update_data["exam_reminder_enabled"])
    if "reminder_time_local" in update_data and "daily_study_reminder_time" not in update_data:
        pref.daily_study_reminder_time = update_data["reminder_time_local"]
    if "daily_study_reminder_time" in update_data and "reminder_time_local" not in update_data:
        pref.reminder_time_local = update_data["daily_study_reminder_time"]

    await db.commit()
    await db.refresh(pref)
    return pref


def _sync_legacy_preference_fields(pref: NotificationPreference) -> None:
    if not getattr(pref, "daily_study_reminder_time", None):
        pref.daily_study_reminder_time = pref.reminder_time_local or "08:00"
    if not getattr(pref, "reminder_time_local", None):
        pref.reminder_time_local = pref.daily_study_reminder_time or "08:00"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_hhmm(value: str | None, fallback: str = "08:00") -> datetime_time:
    raw = value or fallback
    try:
        hour, minute = raw.split(":")
        return datetime_time(hour=int(hour), minute=int(minute))
    except Exception:
        hour, minute = fallback.split(":")
        return datetime_time(hour=int(hour), minute=int(minute))


def _local_now(pref: NotificationPreference) -> datetime:
    try:
        return _utc_now().astimezone(ZoneInfo(pref.timezone or "UTC"))
    except Exception:
        return _utc_now()


def _to_utc(local_date: date, local_time: datetime_time, tz_name: str | None) -> datetime:
    local_dt = datetime.combine(local_date, local_time)
    try:
        return local_dt.replace(tzinfo=ZoneInfo(tz_name or "UTC")).astimezone(timezone.utc)
    except Exception:
        return local_dt.replace(tzinfo=timezone.utc)


def _is_quiet_time(pref: NotificationPreference, at_local: datetime | None = None) -> bool:
    if not pref.quiet_hours_enabled:
        return False
    local_dt = at_local or _local_now(pref)
    start = _parse_hhmm(pref.quiet_hours_start, "22:00")
    end = _parse_hhmm(pref.quiet_hours_end, "07:00")
    current = local_dt.time().replace(second=0, microsecond=0)
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def _respect_quiet_hours(pref: NotificationPreference, scheduled_for: datetime) -> datetime:
    if not pref.quiet_hours_enabled:
        return scheduled_for
    try:
        local_dt = scheduled_for.astimezone(ZoneInfo(pref.timezone or "UTC"))
    except Exception:
        return scheduled_for
    if not _is_quiet_time(pref, local_dt):
        return scheduled_for
    end_time = _parse_hhmm(pref.quiet_hours_end, "07:00")
    end_date = local_dt.date()
    if local_dt.time() >= _parse_hhmm(pref.quiet_hours_start, "22:00"):
        end_date = end_date + timedelta(days=1)
    return _to_utc(end_date, end_time, pref.timezone)


def _dedupe_key(type: str, related_entity_type: str | None, related_entity_id: str | int | None, day: date) -> str:
    return f"{type}:{related_entity_type or 'none'}:{related_entity_id or 'none'}:{day.isoformat()}"


async def create_notification(
    db: AsyncSession,
    user_id: int,
    data: NotificationCreate,
    *,
    deliver_push: bool = True,
    dedupe_key: str | None = None,
) -> Notification:
    if data.type not in NOTIFICATION_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported notification type: {data.type}")

    scheduled_for = data.scheduled_for or _utc_now()
    metadata = dict(data.metadata_json or {})
    if dedupe_key:
        metadata["dedupe_key"] = dedupe_key
        existing = await db.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.metadata_json["dedupe_key"].as_string() == dedupe_key,
            )
        )
        if existing:
            return existing

    notification = Notification(
        user_id=user_id,
        type=data.type,
        title=data.title_ar,
        message=data.body_ar,
        title_ar=data.title_ar,
        body_ar=data.body_ar,
        status="unread",
        priority=data.priority,
        scheduled_for=scheduled_for,
        delivered_at=_utc_now() if scheduled_for <= _utc_now() else None,
        sent_at=None,
        action_url=data.action_url,
        related_entity_type=data.related_entity_type,
        related_entity_id=str(data.related_entity_id) if data.related_entity_id is not None else None,
        metadata_json=metadata,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    if deliver_push and scheduled_for <= _utc_now():
        try:
            pref = await get_preferences(db, user_id)
            if pref.push_enabled:
                results = await notification_delivery_service.send_to_user(db, user_id, notification)
                notification.sent_at = _utc_now()
                notification.delivered_at = notification.delivered_at or notification.sent_at
                notification.metadata_json = {
                    **(notification.metadata_json or {}),
                    "push_results": [result.__dict__ for result in results],
                }
                await db.commit()
                await db.refresh(notification)
        except Exception:
            # Persisted in-app notification remains valid even if push fails.
            await db.rollback()
    return notification


async def send_test_notification(db: AsyncSession, user_id: int) -> Notification:
    return await create_notification(
        db,
        user_id,
        NotificationCreate(
            type="system",
            title_ar="اختبار الإشعارات",
            body_ar="هذه رسالة اختبار من EduMind للتأكد من وصول التذكيرات.",
            priority="normal",
            action_url="/notifications",
            related_entity_type="system",
            related_entity_id="test",
        ),
        dedupe_key=f"system:test:{_utc_now().isoformat()}",
    )


async def rebuild_reminders(db: AsyncSession, user_id: int) -> None:
    """Rebuild legacy pending reminder events from the active study plan."""

    pref = await get_preferences(db, user_id)
    if not pref.in_app_enabled:
        await db.execute(
            delete(ReminderEvent).where(
                and_(ReminderEvent.user_id == user_id, ReminderEvent.status == "pending")
            )
        )
        await db.commit()
        return

    await db.execute(
        delete(ReminderEvent).where(
            and_(ReminderEvent.user_id == user_id, ReminderEvent.status == "pending")
        )
    )

    plan = await _active_study_plan(db, user_id)
    if not plan:
        await db.commit()
        return

    for item in _scheduled_lesson_items(plan):
        lesson_id = item.get("lesson_id")
        item_date = item.get("date")
        if lesson_id is None or not item_date:
            continue
        scheduled_for = _to_utc(item_date, _parse_hhmm(pref.daily_study_reminder_time), pref.timezone)
        db.add(
            ReminderEvent(
                user_id=user_id,
                source_type="lesson",
                source_id=str(lesson_id),
                reminder_type=f"daily:{item_date.isoformat()}",
                scheduled_for=scheduled_for,
                status="pending",
            )
        )
    await db.commit()


async def generate_due_reminders(db: AsyncSession, user_id: int | None = None) -> dict[str, int]:
    """Create due in-app notifications from current learning state."""

    user_ids = [user_id] if user_id is not None else await _user_ids_with_preferences(db)
    counts = {
        "study_reminder": 0,
        "overdue_lesson": 0,
        "exam_countdown": 0,
        "flashcards_due": 0,
        "weak_topic": 0,
    }
    for uid in user_ids:
        pref = await get_preferences(db, uid)
        if not pref.in_app_enabled:
            continue
        local_now = _local_now(pref)
        local_today = local_now.date()
        scheduled_for = _respect_quiet_hours(
            pref,
            _to_utc(local_today, _parse_hhmm(pref.daily_study_reminder_time), pref.timezone),
        )

        if pref.daily_study_reminder_enabled:
            counts["study_reminder"] += await _generate_today_study_reminders(db, uid, pref, local_today, scheduled_for)
        if pref.overdue_lesson_reminder_enabled:
            counts["overdue_lesson"] += await _generate_overdue_lesson_reminders(db, uid, pref, local_today, scheduled_for)
        if pref.exam_reminder_enabled:
            counts["exam_countdown"] += await _generate_exam_countdown_reminders(db, uid, pref, local_today, scheduled_for)
        if pref.flashcards_reminder_enabled:
            counts["flashcards_due"] += await _generate_flashcard_reminders(db, uid, local_today, scheduled_for)
        if pref.weak_topic_reminder_enabled:
            counts["weak_topic"] += await _generate_weak_topic_reminders(db, uid, local_today, scheduled_for)
    return counts


async def _user_ids_with_preferences(db: AsyncSession) -> list[int]:
    result = await db.execute(select(NotificationPreference.user_id))
    return [int(row[0]) for row in result.all()]


async def _active_study_plan(db: AsyncSession, user_id: int) -> StudyPlan | None:
    return await db.scalar(
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id, StudyPlan.status == "active")
        .order_by(StudyPlan.updated_at.desc(), StudyPlan.id.desc())
        .limit(1)
    )


def _scheduled_lesson_items(plan: StudyPlan) -> list[dict[str, Any]]:
    payload = plan.plan_json if isinstance(plan.plan_json, dict) else {}
    schedule = payload.get("schedule") if isinstance(payload, dict) else None
    if not isinstance(schedule, list):
        return []
    items: list[dict[str, Any]] = []
    for day_entry in schedule:
        if not isinstance(day_entry, dict):
            continue
        raw_date = day_entry.get("date")
        try:
            entry_date = date.fromisoformat(str(raw_date))
        except Exception:
            continue
        for session in day_entry.get("sessions") or []:
            if not isinstance(session, dict) or session.get("type") != "lesson":
                continue
            lesson_id = session.get("lesson_id")
            items.append(
                {
                    "date": entry_date,
                    "lesson_id": lesson_id,
                    "title": session.get("title") or session.get("lesson_title") or f"الدرس {lesson_id}",
                    "status": session.get("status") or "not_started",
                }
            )
    return items


async def _lesson_status(db: AsyncSession, user_id: int, lesson_id: Any) -> str:
    try:
        lesson_id_int = int(lesson_id)
    except Exception:
        return "not_started"
    progress = await db.scalar(
        select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id_int)
    )
    return progress.status if progress else "not_started"


async def _generate_today_study_reminders(
    db: AsyncSession,
    user_id: int,
    pref: NotificationPreference,
    local_today: date,
    scheduled_for: datetime,
) -> int:
    plan = await _active_study_plan(db, user_id)
    if not plan:
        return 0
    count = 0
    for item in _scheduled_lesson_items(plan):
        if item["date"] != local_today:
            continue
        if await _lesson_status(db, user_id, item["lesson_id"]) == "completed":
            continue
        dedupe = _dedupe_key("study_reminder", "lesson", item["lesson_id"], local_today)
        await create_notification(
            db,
            user_id,
            NotificationCreate(
                type="study_reminder",
                title_ar="درس اليوم جاهز",
                body_ar=f"حان وقت دراسة {item['title']}",
                priority="normal",
                scheduled_for=scheduled_for,
                action_url="/study-plan?section=today",
                related_entity_type="lesson",
                related_entity_id=item["lesson_id"],
            ),
            dedupe_key=dedupe,
        )
        count += 1
    return count


async def _generate_overdue_lesson_reminders(
    db: AsyncSession,
    user_id: int,
    pref: NotificationPreference,
    local_today: date,
    scheduled_for: datetime,
) -> int:
    plan = await _active_study_plan(db, user_id)
    if not plan:
        return 0
    count = 0
    for item in _scheduled_lesson_items(plan):
        if item["date"] >= local_today:
            continue
        if await _lesson_status(db, user_id, item["lesson_id"]) == "completed":
            continue
        dedupe = _dedupe_key("overdue_lesson", "lesson", item["lesson_id"], local_today)
        await create_notification(
            db,
            user_id,
            NotificationCreate(
                type="overdue_lesson",
                title_ar="لديك درس متأخر",
                body_ar=f"{item['title']} لم يكتمل بعد",
                priority="high",
                scheduled_for=scheduled_for,
                action_url="/study-plan?section=today",
                related_entity_type="lesson",
                related_entity_id=item["lesson_id"],
            ),
            dedupe_key=dedupe,
        )
        count += 1
    return count


async def _generate_exam_countdown_reminders(
    db: AsyncSession,
    user_id: int,
    pref: NotificationPreference,
    local_today: date,
    scheduled_for: datetime,
) -> int:
    plan = await _active_study_plan(db, user_id)
    if not plan or not plan.exam_date:
        return 0
    days = (plan.exam_date - local_today).days
    if days not in {7, 3, 1}:
        return 0
    dedupe = _dedupe_key("exam_countdown", "plan", plan.id, local_today)
    await create_notification(
        db,
        user_id,
        NotificationCreate(
            type="exam_countdown",
            title_ar="اقترب اختبار الكيمياء",
            body_ar=f"تبقّى {days} أيام على الاختبار",
            priority="high",
            scheduled_for=scheduled_for,
            action_url="/study-plan?section=review",
            related_entity_type="plan",
            related_entity_id=plan.id,
        ),
        dedupe_key=dedupe,
    )
    return 1


async def _generate_flashcard_reminders(
    db: AsyncSession,
    user_id: int,
    local_today: date,
    scheduled_for: datetime,
) -> int:
    due_count = await db.scalar(
        select(func.count(Flashcard.id))
        .outerjoin(
            FlashcardProgress,
            (FlashcardProgress.flashcard_id == Flashcard.id) & (FlashcardProgress.user_id == user_id),
        )
        .where(
            or_(
                FlashcardProgress.id.is_(None),
                FlashcardProgress.mastered.is_(False),
                FlashcardProgress.next_review_at.is_(None),
                FlashcardProgress.next_review_at <= local_today,
            )
        )
    )
    count = int(due_count or 0)
    if count <= 0:
        return 0
    dedupe = _dedupe_key("flashcards_due", "flashcards", "due", local_today)
    await create_notification(
        db,
        user_id,
        NotificationCreate(
            type="flashcards_due",
            title_ar="بطاقات جاهزة للمراجعة",
            body_ar=f"لديك {count} بطاقة مستحقة اليوم",
            priority="normal",
            scheduled_for=scheduled_for,
            action_url="/flashcards",
            related_entity_type="flashcard",
            related_entity_id="due",
        ),
        dedupe_key=dedupe,
    )
    return 1


async def _generate_weak_topic_reminders(
    db: AsyncSession,
    user_id: int,
    local_today: date,
    scheduled_for: datetime,
) -> int:
    progress = await db.scalar(
        select(UserProgress)
        .where(UserProgress.user_id == user_id, UserProgress.best_quiz_score < 60)
        .order_by(UserProgress.best_quiz_score.asc(), UserProgress.updated_at.desc() if hasattr(UserProgress, "updated_at") else UserProgress.id.desc())
        .limit(1)
    )
    if progress is None:
        return 0
    topic = await db.get(Topic, progress.topic_id)
    topic_title = topic.title_ar if topic else "موضوع كيميائي"
    dedupe = _dedupe_key("weak_topic", "topic", progress.topic_id, local_today)
    await create_notification(
        db,
        user_id,
        NotificationCreate(
            type="weak_topic",
            title_ar="نقطة ضعف تحتاج تدريب",
            body_ar=f"موضوع {topic_title} يحتاج مراجعة قصيرة",
            priority="normal",
            scheduled_for=scheduled_for,
            action_url="/quiz",
            related_entity_type="topic",
            related_entity_id=progress.topic_id,
        ),
        dedupe_key=dedupe,
    )
    return 1
