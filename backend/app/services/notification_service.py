"""Service for managing notifications and reminders."""

from datetime import date, datetime, timedelta, timezone, time as datetime_time
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chemistry import Lesson
from app.models.notification import Notification, NotificationPreference, ReminderEvent
from app.models.study_plan import StudyPlan
from app.schemas.notification import NotificationPreferenceUpdate


async def get_notifications(db: AsyncSession, user_id: int) -> list[Notification]:
    """Retrieve all notifications for a user, sorted chronologically descending."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.scheduled_for.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    """Get count of unread notifications for a user."""
    stmt = select(func.count(Notification.id)).where(
        and_(Notification.user_id == user_id, Notification.status == "unread")
    )
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def mark_read(db: AsyncSession, user_id: int, notif_id: int) -> Notification:
    """Mark a single notification as read."""
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.status = "read"
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return notif


async def mark_all_read(db: AsyncSession, user_id: int) -> None:
    """Mark all unread notifications for a user as read."""
    stmt = (
        select(Notification)
        .where(and_(Notification.user_id == user_id, Notification.status == "unread"))
    )
    result = await db.execute(stmt)
    unreads = result.scalars().all()
    now = datetime.now(timezone.utc)
    for notif in unreads:
        notif.status = "read"
        notif.read_at = now
    await db.commit()


async def delete_notification(db: AsyncSession, user_id: int, notif_id: int) -> None:
    """Delete (or archive) a notification."""
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    await db.commit()


async def get_preferences(db: AsyncSession, user_id: int) -> NotificationPreference:
    """Retrieve or create notification preferences for a user."""
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()
    
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return pref


async def update_preferences(
    db: AsyncSession, user_id: int, updates: NotificationPreferenceUpdate
) -> NotificationPreference:
    """Update notification preferences for a user."""
    pref = await get_preferences(db, user_id)
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pref, key, value)
    await db.commit()
    await db.refresh(pref)
    return pref


async def rebuild_reminders(db: AsyncSession, user_id: int) -> None:
    """Rebuild pending reminder events from the user's active study plan."""
    pref = await get_preferences(db, user_id)
    if not pref.in_app_enabled:
        await db.execute(
            delete(ReminderEvent).where(
                and_(
                    ReminderEvent.user_id == user_id,
                    ReminderEvent.status == "pending",
                )
            )
        )
        await db.commit()
        return

    # Delete all future pending reminders for this user
    del_stmt = delete(ReminderEvent).where(
        and_(
            ReminderEvent.user_id == user_id,
            ReminderEvent.status == "pending"
        )
    )
    await db.execute(del_stmt)

    # Fetch active study plan
    plan_stmt = select(StudyPlan).where(
        and_(
            StudyPlan.user_id == user_id,
            StudyPlan.status == "active"
        )
    )
    plan_result = await db.execute(plan_stmt)
    plan = plan_result.scalar_one_or_none()
    if not plan:
        await db.commit()
        return

    reminder_time_str = pref.reminder_time_local
    tz_name = pref.timezone or "UTC"
    
    try:
        hours, mins = map(int, reminder_time_str.split(":"))
    except ValueError:
        hours, mins = 8, 0

    local_time = datetime_time(hour=hours, minute=mins)
    now = datetime.now(timezone.utc)

    async def add_event_if_missing(source_type: str, source_id: str, reminder_type: str, scheduled_for: datetime) -> None:
        exists_stmt = select(ReminderEvent.id).where(
            and_(
                ReminderEvent.user_id == user_id,
                ReminderEvent.source_type == source_type,
                ReminderEvent.source_id == source_id,
                ReminderEvent.reminder_type == reminder_type,
            )
        )
        exists_result = await db.execute(exists_stmt)
        if exists_result.scalar_one_or_none() is not None:
            return
        db.add(
            ReminderEvent(
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                reminder_type=reminder_type,
                scheduled_for=scheduled_for,
                status="pending",
            )
        )

    # 1. Generate Exam Reminders if target date is set
    if pref.exam_reminders_enabled and plan.exam_date:
        # Assume exam time is 09:00 AM local time
        exam_local = datetime.combine(plan.exam_date, datetime_time(9, 0))
        try:
            exam_tz = exam_local.replace(tzinfo=ZoneInfo(tz_name))
            exam_utc = exam_tz.astimezone(timezone.utc)
        except Exception:
            exam_utc = exam_local.replace(tzinfo=timezone.utc)

        exam_rules = [
            ("7_days_before", exam_utc - timedelta(days=7)),
            ("3_days_before", exam_utc - timedelta(days=3)),
            ("1_day_before", exam_utc - timedelta(days=1)),
            ("2_hours_before", exam_utc - timedelta(hours=2)),
            ("at_exam_time", exam_utc),
        ]

        for r_type, sched_time in exam_rules:
            if sched_time > now:
                await add_event_if_missing("exam", str(plan.id), r_type, sched_time)

    # 2. Generate Lesson Reminders
    if not pref.lesson_reminders_enabled:
        await db.commit()
        return

    # Fetch all curriculum lessons in order
    lessons_stmt = select(Lesson).order_by(Lesson.order)
    lessons_result = await db.execute(lessons_stmt)
    lessons = list(lessons_result.scalars().all())

    # Extract selected lesson IDs if configured in plan_json
    lesson_ids = []
    start_date = date.today()
    study_days = ["ن", "ث", "ر", "خ", "ج"]  # Mon to Fri

    if plan.plan_json and isinstance(plan.plan_json, dict):
        config = plan.plan_json.get("config") or plan.plan_json
        if isinstance(config, dict):
            lesson_ids = config.get("lessonIds") or config.get("lesson_ids") or []
            
            # Extract start date
            start_date_str = config.get("startDate") or config.get("start_date")
            if start_date_str:
                try:
                    start_date = date.fromisoformat(start_date_str)
                except ValueError:
                    pass
            
            # Extract study days
            if "studyDays" in config:
                study_days = config.get("studyDays") or []
            elif "study_days" in config:
                study_days = config.get("study_days") or []

    if lesson_ids:
        str_ids = [str(lid) for lid in lesson_ids]
        lessons = [lesson for lesson in lessons if str(lesson.id) in str_ids or lesson.id in lesson_ids]

    # Map Arabic study days to weekday index (0=Mon, 1=Tue, ..., 6=Sun)
    day_map = {"ن": 0, "ث": 1, "ر": 2, "خ": 3, "ج": 4, "س": 5, "ح": 6}
    study_day_ints = [day_map[d] for d in study_days if d in day_map]
    if not study_day_ints:
        study_day_ints = [0, 1, 2, 3, 4]  # Default to weekdays

    # Distribute lessons chronologically starting from start_date
    curr_date = start_date
    scheduled_lessons = []
    lesson_idx = 0

    while lesson_idx < len(lessons):
        if curr_date.weekday() in study_day_ints:
            scheduled_lessons.append((lessons[lesson_idx], curr_date))
            lesson_idx += 1
        curr_date += timedelta(days=1)

    # Create reminder events for each distributed lesson
    for lesson, l_date in scheduled_lessons:
        # Lesson time on scheduled date
        lesson_local = datetime.combine(l_date, local_time)
        try:
            lesson_tz = lesson_local.replace(tzinfo=ZoneInfo(tz_name))
            lesson_utc = lesson_tz.astimezone(timezone.utc)
        except Exception:
            lesson_utc = lesson_local.replace(tzinfo=timezone.utc)

        lesson_rules = [
            ("1_day_before", lesson_utc - timedelta(days=1)),
            ("morning_of", lesson_utc.replace(hour=8, minute=0) if lesson_utc.hour > 8 else lesson_utc - timedelta(hours=2)),
            ("30_minutes_before", lesson_utc - timedelta(minutes=30)),
            ("at_lesson_start_time", lesson_utc),
        ]

        for r_type, sched_time in lesson_rules:
            if sched_time > now:
                await add_event_if_missing("lesson", str(lesson.id), r_type, sched_time)

    await db.commit()
