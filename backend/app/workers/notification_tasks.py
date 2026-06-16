"""Celery tasks for processing notifications and reminders."""

from datetime import datetime, timezone
import logging

from sqlalchemy import and_, select

from app.database import SessionLocal
from app.models.chemistry import Lesson
from app.models.notification import Notification, NotificationPreference, ReminderEvent
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.notification_tasks.check_pending_reminders")
def check_pending_reminders() -> str:
    """Scan and process pending reminder events where scheduled_for <= now."""
    now = datetime.now(timezone.utc)
    sent_count = 0
    skipped_count = 0
    failed_count = 0
    
    with SessionLocal() as db:
        # Query pending reminder events scheduled for <= now
        stmt = select(ReminderEvent).where(
            and_(
                ReminderEvent.status == "pending",
                ReminderEvent.scheduled_for <= now
            )
        )
        events = db.scalars(stmt).all()
        
        for event in events:
            # Check user preference
            pref_stmt = select(NotificationPreference).where(NotificationPreference.user_id == event.user_id)
            pref = db.scalar(pref_stmt)
            
            # Default preferences to True if not explicitly configured
            exam_enabled = pref.exam_reminders_enabled if pref and pref.exam_reminders_enabled is not None else True
            lesson_enabled = pref.lesson_reminders_enabled if pref and pref.lesson_reminders_enabled is not None else True
            in_app_enabled = pref.in_app_enabled if pref and pref.in_app_enabled is not None else True
            
            if not in_app_enabled:
                event.status = "skipped"
                db.add(event)
                skipped_count += 1
                continue
            if event.source_type == "exam" and not exam_enabled:
                event.status = "skipped"
                db.add(event)
                skipped_count += 1
                continue
            if event.source_type == "lesson" and not lesson_enabled:
                event.status = "skipped"
                db.add(event)
                skipped_count += 1
                continue

            # Build Notification message parameters based on types
            title = ""
            message = ""
            notif_type = ""
            priority = "normal"
            action_url = ""

            if event.source_type == "exam":
                notif_type = "exam_reminder"
                priority = "high"
                action_url = "/study-plan"
                
                if event.reminder_type == "7_days_before":
                    title = "متبقي 7 أيام على الامتحان!"
                    message = "الامتحان يقترب. تأكد من مراجعة الدروس الصعبة وحل الاختبارات التجريبية."
                elif event.reminder_type == "3_days_before":
                    title = "متبقي 3 أيام على الامتحان!"
                    message = "حان وقت المراجعة المكثفة والتركيز على نقاط الضعف."
                elif event.reminder_type == "1_day_before":
                    title = "غداً هو يوم الامتحان!"
                    message = "متبقي يوم واحد فقط. احصل على قسط كافٍ من النوم وراجع الملخصات السريعة."
                elif event.reminder_type == "2_hours_before":
                    title = "ساعتان قبل الامتحان!"
                    message = "الامتحان يبدأ بعد ساعتين. استعد وراجع المفاهيم الأساسية."
                elif event.reminder_type == "at_exam_time":
                    title = "حان وقت الامتحان!"
                    message = "بالتوفيق في امتحان الكيمياء الخاص بك اليوم! ثق بقدراتك."
                    priority = "urgent"
                else:
                    title = "تذكير بالامتحان"
                    message = "لديك موعد امتحان كيمياء مجدول قريباً."

            elif event.source_type == "lesson":
                notif_type = "lesson_reminder"
                action_url = f"/lessons/{event.source_id}"
                
                # Retrieve lesson title to construct a descriptive reminder message
                lesson = db.get(Lesson, int(event.source_id)) if event.source_id.isdigit() else None
                lesson_title = lesson.title_ar if lesson else f"الدرس {event.source_id}"

                if event.reminder_type == "1_day_before":
                    title = "درس غدٍ مجدول"
                    message = f"لديك درس غداً: '{lesson_title}'. تأكد من تخصيص وقت له."
                elif event.reminder_type == "morning_of":
                    title = "مهمة المذاكرة اليوم"
                    message = f"صباح الخير! جدولك اليوم يتضمن درس: '{lesson_title}'."
                elif event.reminder_type == "30_minutes_before":
                    title = "30 دقيقة على موعد الدرس"
                    message = f"سيبدأ درسك: '{lesson_title}' بعد 30 دقيقة. جهز دفتر ملاحظاتك."
                elif event.reminder_type == "at_lesson_start_time":
                    title = "حان وقت درس الكيمياء!"
                    message = f"ابدأ دراسة: '{lesson_title}' الآن وحافظ على استمراريتك."
                else:
                    title = "تذكير بدرس الكيمياء"
                    message = f"حان موعد مذاكرة درسك اليوم: {lesson_title}."
            else:
                event.status = "skipped"
                db.add(event)
                skipped_count += 1
                continue

            # Check for duplicate notifications to avoid double delivery.
            notif_dup_stmt = select(Notification).where(
                and_(
                    Notification.user_id == event.user_id,
                    Notification.type == notif_type,
                    Notification.scheduled_for == event.scheduled_for,
                    Notification.action_url == action_url,
                )
            )
            notif_dup = db.scalar(notif_dup_stmt)
            if notif_dup:
                event.status = "sent"
                event.notification_id = notif_dup.id
                db.add(event)
                skipped_count += 1
                continue

            try:
                notification = Notification(
                    user_id=event.user_id,
                    type=notif_type,
                    title=title,
                    message=message,
                    status="unread",
                    priority=priority,
                    scheduled_for=event.scheduled_for,
                    delivered_at=now,
                    action_url=action_url,
                    metadata_json={
                        "source_type": event.source_type,
                        "source_id": str(event.source_id),
                        "reminder_type": event.reminder_type,
                    }
                )
                db.add(notification)
                db.flush()  # Populate notification.id

                event.status = "sent"
                event.notification_id = notification.id
                db.add(event)
                sent_count += 1
            except Exception:
                logger.exception("Failed to deliver reminder event %s", event.id)
                event.status = "failed"
                db.add(event)
                failed_count += 1

        db.commit()

    return f"Processed reminders. Sent: {sent_count}, Skipped: {skipped_count}, Failed: {failed_count}"
