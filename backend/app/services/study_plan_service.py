from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chemistry import Chapter, Lesson, LessonProgress
from app.models.study_plan import StudyPlan
from app.schemas.study_plans import StudyPlanCreate, StudyPlanGenerateRequest, StudyPlanUpdate

WEEKDAYS: dict[str, dict[str, Any]] = {
    "sun": {"index": 6, "ar": "الأحد", "aliases": {"sun", "sunday", "الأحد", "احد", "ح"}},
    "mon": {"index": 0, "ar": "الاثنين", "aliases": {"mon", "monday", "الاثنين", "إثنين", "اثنين", "ن"}},
    "tue": {"index": 1, "ar": "الثلاثاء", "aliases": {"tue", "tuesday", "الثلاثاء", "ثلاثاء", "ث"}},
    "wed": {"index": 2, "ar": "الأربعاء", "aliases": {"wed", "wednesday", "الأربعاء", "اربعاء", "أربعاء", "ر"}},
    "thu": {"index": 3, "ar": "الخميس", "aliases": {"thu", "thursday", "الخميس", "خميس", "خ"}},
    "fri": {"index": 4, "ar": "الجمعة", "aliases": {"fri", "friday", "الجمعة", "جمعه", "جمعة", "ج"}},
    "sat": {"index": 5, "ar": "السبت", "aliases": {"sat", "saturday", "السبت", "سبت", "س"}},
}
DEFAULT_STUDY_DAYS = ["sun", "mon", "tue", "wed", "thu"]
ALL_STUDY_DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]


async def get_study_plans(db: AsyncSession, user_id: int) -> list[StudyPlan]:
    result = await db.execute(select(StudyPlan).where(StudyPlan.user_id == user_id).order_by(StudyPlan.created_at.desc()))
    return list(result.scalars().all())

async def get_study_plan(db: AsyncSession, plan_id: int, user_id: int) -> StudyPlan:
    plan = await db.get(StudyPlan, plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return plan

async def create_study_plan(db: AsyncSession, user_id: int, request: StudyPlanCreate) -> StudyPlan:
    plan = StudyPlan(**request.model_dump(), user_id=user_id)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _today() -> date:
    return date.today()


def _parse_requested_date(value: str | None, field_name: str) -> date | None:
    if value is None or value == "":
        return None
    parsed = _parse_date(value)
    if parsed is None:
        raise HTTPException(status_code=422, detail=f"{field_name} must be a valid ISO date")
    return parsed


def _validate_plan_dates(request: StudyPlanGenerateRequest) -> tuple[date, date, date | None]:
    today = _today()
    start_date = _parse_requested_date(request.startDate, "startDate") or today
    exam_date = _parse_requested_date(request.examDate, "examDate")
    end_date = exam_date or _parse_requested_date(request.endDate, "endDate") or (start_date + timedelta(days=120))

    if start_date < today or start_date.year < today.year:
        raise HTTPException(status_code=422, detail="Study plan startDate cannot be before today or a previous year")
    if end_date <= start_date:
        raise HTTPException(status_code=422, detail="Study plan endDate/examDate must be after startDate")
    return start_date, end_date, exam_date


def _lesson_ids(raw: list[str | int]) -> list[int]:
    ids: list[int] = []
    invalid_values: list[str] = []
    for item in raw:
        try:
            lesson_id = int(item)
        except (TypeError, ValueError):
            invalid_values.append(str(item))
            continue
        if lesson_id <= 0:
            invalid_values.append(str(item))
            continue
        if lesson_id not in ids:
            ids.append(lesson_id)
    if invalid_values:
        raise HTTPException(status_code=422, detail="lessonIds must contain valid positive lesson IDs")
    if not ids:
        raise HTTPException(status_code=422, detail="Study plan generation requires at least one selected lesson")
    return ids


def _normalize_study_day(day: str) -> str | None:
    value = str(day).strip().lower()
    for code, meta in WEEKDAYS.items():
        aliases = {str(alias).strip().lower() for alias in meta["aliases"]}
        if value == code or value in aliases:
            return code
    return None


def _normalize_study_days(raw_days: list[str], *, use_exam_defaults: bool) -> list[str]:
    normalized: list[str] = []
    for day in raw_days:
        code = _normalize_study_day(day)
        if code and code not in normalized:
            normalized.append(code)
    if normalized:
        return normalized
    return ALL_STUDY_DAYS.copy() if use_exam_defaults else DEFAULT_STUDY_DAYS.copy()


def _number_from_text(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", value)
    if match:
        return float(match.group(0))
    arabic_numbers = {
        "واحدة": 1,
        "واحد": 1,
        "ساعتان": 2,
        "ساعتين": 2,
        "اثنتان": 2,
        "اثنين": 2,
        "ثلاث": 3,
        "أربع": 4,
        "اربع": 4,
    }
    for word, number in arabic_numbers.items():
        if word in value:
            return float(number)
    return None


def _hours_from_value(value: float | int | str | None, *, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else default
    if not value:
        return default

    text = str(value).strip()
    number = _number_from_text(text)
    if number is None:
        return default
    if "دقيقة" in text:
        return max(1.0, number / 60)
    return max(0.25, number)


def _hours_by_day(request: StudyPlanGenerateRequest, study_days: list[str]) -> dict[str, float]:
    if request.studyHoursByDay:
        hours: dict[str, float] = {}
        for day, value in request.studyHoursByDay.items():
            code = _normalize_study_day(day)
            if code and code in study_days:
                hours[code] = round(_hours_from_value(value, default=1.0), 2)
        missing = [day for day in study_days if day not in hours]
        if not missing:
            return hours
    else:
        hours = {}
        missing = study_days

    default_source = request.dailyStudyHours if request.dailyStudyHours is not None else request.lessonDuration
    default_hours = _hours_from_value(default_source, default=1.0)
    for day in missing:
        hours[day] = round(default_hours, 2)
    return hours


def _date_range(start_date: date, end_date: date) -> list[date]:
    days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=offset) for offset in range(days)]


def _schedule_dates(start_date: date, end_date: date, study_days: list[str]) -> list[date]:
    allowed_indexes = {WEEKDAYS[day]["index"] for day in study_days}
    return [day for day in _date_range(start_date, end_date) if day.weekday() in allowed_indexes]


def _lesson_schedule_items(lessons: list[Lesson]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for lesson in lessons:
        duration = lesson.duration_min if lesson.duration_min and lesson.duration_min > 0 else 45
        unit = lesson.chapter.unit if lesson.chapter and lesson.chapter.unit else None
        items.append(
            {
                "lesson_id": lesson.id,
                "title": lesson.title_ar,
                "chapter_id": lesson.chapter_id,
                "unit_id": unit.id if unit else None,
                "unit_number": unit.unit_number if unit else None,
                "duration_minutes": duration,
                "remaining_minutes": duration,
            }
        )
    return items


def _build_schedule(
    *,
    lessons: list[Lesson],
    start_date: date,
    end_date: date,
    study_days: list[str],
    hours: dict[str, float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lesson_items = _lesson_schedule_items(lessons)
    dates = _schedule_dates(start_date, end_date, study_days)
    lesson_index = 0
    total_planned_minutes = 0
    capacity_minutes = 0
    schedule: list[dict[str, Any]] = []

    for study_date in dates:
        weekday = next(code for code, meta in WEEKDAYS.items() if meta["index"] == study_date.weekday())
        planned_minutes = int(round(hours.get(weekday, 1.0) * 60))
        capacity_minutes += planned_minutes
        remaining_capacity = planned_minutes
        sessions: list[dict[str, Any]] = []

        while lesson_index < len(lesson_items) and remaining_capacity > 0:
            item = lesson_items[lesson_index]
            chunk_minutes = min(remaining_capacity, int(item["remaining_minutes"]))
            if chunk_minutes <= 0:
                lesson_index += 1
                continue
            total_duration = int(item["duration_minutes"])
            is_continuation = int(item["remaining_minutes"]) < total_duration
            item["remaining_minutes"] = int(item["remaining_minutes"]) - chunk_minutes
            remaining_capacity -= chunk_minutes
            total_planned_minutes += chunk_minutes
            sessions.append(
                {
                    "type": "lesson",
                    "lesson_id": item["lesson_id"],
                    "title": item["title"],
                    "chapter_id": item["chapter_id"],
                    "unit_id": item["unit_id"],
                    "unit_number": item["unit_number"],
                    "minutes": chunk_minutes,
                    "status": "planned",
                    "completed": False,
                    "is_continuation": is_continuation,
                }
            )
            if item["remaining_minutes"] <= 0:
                lesson_index += 1

        if lesson_index >= len(lesson_items) and lessons and remaining_capacity >= 30:
            review_minutes = min(45, remaining_capacity)
            total_planned_minutes += review_minutes
            sessions.append(
                {
                    "type": "review",
                    "title": "مراجعة تراكمية",
                    "minutes": review_minutes,
                    "status": "planned",
                    "completed": False,
                }
            )

        schedule.append(
            {
                "date": study_date.isoformat(),
                "weekday": weekday,
                "weekday_ar": WEEKDAYS[weekday]["ar"],
                "planned_hours": round(planned_minutes / 60, 2),
                "planned_minutes": planned_minutes,
                "sessions": sessions,
            }
        )

    warnings: list[str] = []
    over_capacity = lesson_index < len(lesson_items)
    if not dates:
        warnings.append("لا توجد أيام دراسة ضمن الفترة المحددة.")
    if over_capacity:
        remaining_lessons = len(lesson_items) - lesson_index
        warnings.append(f"الوقت المتاح لا يكفي لإنهاء كل الدروس. تبقى {remaining_lessons} درس/أجزاء درس.")

    return schedule, {
        "total_study_days": len(dates),
        "weekly_hours": round(sum(hours.values()), 2),
        "hours_by_day": hours,
        "total_planned_minutes": total_planned_minutes,
        "capacity_minutes": capacity_minutes,
        "over_capacity": over_capacity,
        "warnings": warnings,
    }


def _task_id(*parts: object) -> str:
    normalized = [
        re.sub(r"[^a-zA-Z0-9_-]+", "-", str(part).strip()).strip("-")
        for part in parts
        if part is not None and str(part).strip()
    ]
    return "-".join(normalized).lower()


def _task_from_session(entry: dict[str, Any], session: dict[str, Any], session_index: int) -> dict[str, Any]:
    session_type = str(session.get("type") or "review")
    lesson_id = _as_int(session.get("lesson_id"))
    task_type = "lesson" if session_type == "lesson" and lesson_id else "review"
    return {
        "id": _task_id("task", entry.get("date"), task_type, lesson_id or session_index),
        "type": task_type,
        "title": str(session.get("title") or ("مراجعة" if task_type == "review" else "درس")),
        "lesson_id": lesson_id,
        "topic_id": None,
        "estimated_minutes": int(session.get("minutes") or entry.get("planned_minutes") or 20),
        "status": "completed" if session.get("completed") is True or session.get("status") == "completed" else "pending",
        "completed_at": session.get("completed_at"),
    }


def _build_plan_weeks(schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weeks: list[dict[str, Any]] = []
    current_week: dict[str, Any] | None = None
    previous_iso_week: tuple[int, int] | None = None

    for entry in schedule:
        scheduled_date = _parse_date(str(entry.get("date") or ""))
        if scheduled_date is None:
            continue
        iso_year, iso_week, _ = scheduled_date.isocalendar()
        iso_key = (iso_year, iso_week)
        if current_week is None or previous_iso_week != iso_key:
            current_week = {
                "week_number": len(weeks) + 1,
                "focus": "تغطية الدروس المجدولة ومراجعة قصيرة",
                "days": [],
            }
            weeks.append(current_week)
            previous_iso_week = iso_key

        sessions = entry.get("sessions") if isinstance(entry.get("sessions"), list) else []
        tasks = [
            _task_from_session(entry, session, index)
            for index, session in enumerate(sessions, start=1)
            if isinstance(session, dict)
        ]
        lesson_ids = [
            task["lesson_id"]
            for task in tasks
            if task["lesson_id"] is not None
        ]
        unique_lesson_ids = list(dict.fromkeys(lesson_ids))
        if unique_lesson_ids:
            tasks.append(
                {
                    "id": _task_id("task", entry.get("date"), "flashcards", "-".join(map(str, unique_lesson_ids))),
                    "type": "flashcards",
                    "title": "مراجعة بطاقات الدروس المجدولة",
                    "lesson_id": unique_lesson_ids[0],
                    "topic_id": None,
                    "estimated_minutes": 10,
                    "status": "pending",
                    "completed_at": None,
                }
            )
        if len(unique_lesson_ids) >= 2:
            tasks.append(
                {
                    "id": _task_id("task", entry.get("date"), "quiz", "-".join(map(str, unique_lesson_ids))),
                    "type": "quiz",
                    "title": "اختبار قصير للدروس المجدولة",
                    "lesson_id": unique_lesson_ids[0],
                    "topic_id": None,
                    "estimated_minutes": 15,
                    "status": "pending",
                    "completed_at": None,
                }
            )

        current_week["days"].append(
            {
                "date": scheduled_date.isoformat(),
                "title": f"خطة {entry.get('weekday_ar') or scheduled_date.isoformat()}",
                "lesson_ids": unique_lesson_ids,
                "topic_ids": [],
                "tasks": tasks,
            }
        )

    return weeks


def _validate_plan_json_contract(plan_json: dict[str, Any]) -> None:
    weeks = plan_json.get("weeks")
    if not isinstance(weeks, list):
        raise HTTPException(status_code=500, detail="Generated study plan is missing weeks")
    for week in weeks:
        days = week.get("days") if isinstance(week, dict) else None
        if not isinstance(days, list):
            raise HTTPException(status_code=500, detail="Generated study plan week is invalid")
        for day in days:
            tasks = day.get("tasks") if isinstance(day, dict) else None
            if not isinstance(tasks, list):
                raise HTTPException(status_code=500, detail="Generated study plan day is invalid")
            for task in tasks:
                if not isinstance(task, dict) or not task.get("id") or task.get("status") not in {"pending", "completed", "skipped"}:
                    raise HTTPException(status_code=500, detail="Generated study plan task is invalid")


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _scheduled_lesson_ids(metadata: dict[str, Any]) -> list[int]:
    schedule = metadata.get("schedule") if isinstance(metadata.get("schedule"), list) else []
    lesson_ids: list[int] = []
    for entry in schedule:
        if not isinstance(entry, dict):
            continue
        sessions = entry.get("sessions") if isinstance(entry.get("sessions"), list) else []
        for session in sessions:
            if not isinstance(session, dict) or session.get("type") != "lesson":
                continue
            lesson_id = _as_int(session.get("lesson_id"))
            if lesson_id and lesson_id not in lesson_ids:
                lesson_ids.append(lesson_id)
    return lesson_ids


def _lesson_title(lesson_id: int, lesson: Lesson | None, fallback_title: str | None) -> str:
    if lesson and lesson.title_ar:
        return lesson.title_ar
    return fallback_title or f"درس {lesson_id}"


def _unit_title(lesson: Lesson | None, unit_number: int | None = None) -> str | None:
    unit = lesson.chapter.unit if lesson and lesson.chapter and lesson.chapter.unit else None
    if unit and unit.title_ar:
        return unit.title_ar
    if unit and unit.unit_number:
        return f"الوحدة {unit.unit_number}"
    if unit_number:
        return f"الوحدة {unit_number}"
    return None


def _chapter_title(lesson: Lesson | None) -> str | None:
    if lesson and lesson.chapter and lesson.chapter.title_ar:
        return lesson.chapter.title_ar
    return None


def _progress_status(progress: LessonProgress | None) -> str | None:
    if not progress or not progress.status:
        return None
    if progress.status in {"not_started", "in_progress", "completed", "skipped"}:
        return progress.status
    return None


def _expected_progress_percent(metadata: dict[str, Any], today: date) -> float:
    summary = metadata.get("summary") if isinstance(metadata.get("summary"), dict) else {}
    config = metadata.get("config") if isinstance(metadata.get("config"), dict) else {}
    start_date = _parse_date(str(summary.get("start_date") or config.get("startDate") or ""))
    end_date = _parse_date(str(summary.get("end_date") or config.get("endDate") or config.get("examDate") or ""))
    if not start_date or not end_date or end_date <= start_date:
        return 0.0
    if today <= start_date:
        return 0.0
    if today >= end_date:
        return 100.0
    elapsed_days = (today - start_date).days
    total_days = max((end_date - start_date).days, 1)
    return round(min(100.0, max(0.0, (elapsed_days / total_days) * 100)), 1)


def _track_status(actual_percent: float, expected_percent: float) -> str:
    if actual_percent >= expected_percent + 10:
        return "ahead"
    if actual_percent >= expected_percent - 10:
        return "on_track"
    return "behind"


def _build_study_plan_progress(
    *,
    plan: StudyPlan,
    lessons_by_id: dict[int, Lesson],
    progress_by_lesson_id: dict[int, LessonProgress],
    today: date,
) -> dict[str, Any]:
    metadata = plan.plan_json if isinstance(plan.plan_json, dict) else {}
    schedule = metadata.get("schedule") if isinstance(metadata.get("schedule"), list) else []
    completed_ids = {int(item) for item in metadata.get("completed_lesson_ids", []) if str(item).isdigit()}
    lesson_records: dict[int, dict[str, Any]] = {}

    for entry in schedule:
        if not isinstance(entry, dict):
            continue
        scheduled_date = _parse_date(str(entry.get("date") or ""))
        sessions = entry.get("sessions") if isinstance(entry.get("sessions"), list) else []
        for session in sessions:
            if not isinstance(session, dict) or session.get("type") != "lesson":
                continue
            lesson_id = _as_int(session.get("lesson_id"))
            if lesson_id is None:
                continue
            record = lesson_records.setdefault(
                lesson_id,
                {
                    "lesson_id": lesson_id,
                    "fallback_title": session.get("title"),
                    "scheduled_date": scheduled_date,
                    "estimated_minutes": 0,
                    "completed_minutes": 0,
                    "session_count": 0,
                    "completed_session_count": 0,
                    "unit_number": session.get("unit_number"),
                },
            )
            if scheduled_date and (
                record["scheduled_date"] is None or scheduled_date < record["scheduled_date"]
            ):
                record["scheduled_date"] = scheduled_date
            minutes = int(session.get("minutes") or 0)
            record["estimated_minutes"] += max(0, minutes)
            record["session_count"] += 1
            if session.get("completed") is True or session.get("status") == "completed":
                record["completed_session_count"] += 1
                record["completed_minutes"] += max(0, minutes)

    scheduled_lessons: list[dict[str, Any]] = []
    for index, record in enumerate(
        sorted(
            lesson_records.values(),
            key=lambda item: (item["scheduled_date"] or date.max, item["lesson_id"]),
        ),
        start=1,
    ):
        lesson_id = int(record["lesson_id"])
        lesson = lessons_by_id.get(lesson_id)
        progress_record = progress_by_lesson_id.get(lesson_id)
        source_status = _progress_status(progress_record)
        is_completed = (
            lesson_id in completed_ids
            or source_status == "completed"
            or (
                record["session_count"] > 0
                and record["completed_session_count"] == record["session_count"]
            )
        )
        if is_completed:
            status = "completed"
            completion_percent = 100.0
        elif source_status == "skipped":
            status = "skipped"
            completion_percent = 0.0
        else:
            estimated_minutes = max(int(record["estimated_minutes"]), 1)
            completion_percent = round((int(record["completed_minutes"]) / estimated_minutes) * 100, 1)
            if source_status == "in_progress" or completion_percent > 0:
                status = "in_progress"
                completion_percent = max(completion_percent, 50.0 if source_status == "in_progress" else completion_percent)
            else:
                status = "not_started"
            if record["scheduled_date"] and record["scheduled_date"] < today:
                status = "overdue"

        scheduled_lessons.append(
            {
                "study_plan_item_id": index,
                "lesson_id": lesson_id,
                "lesson_title_ar": _lesson_title(lesson_id, lesson, record.get("fallback_title")),
                "unit_id": lesson.chapter.unit.id if lesson and lesson.chapter and lesson.chapter.unit else None,
                "unit_title_ar": _unit_title(lesson, _as_int(record.get("unit_number"))),
                "chapter_title_ar": _chapter_title(lesson),
                "scheduled_date": record["scheduled_date"].isoformat() if record["scheduled_date"] else None,
                "status": status,
                "completion_percent": completion_percent,
                "estimated_minutes": int(record["estimated_minutes"]),
            }
        )

    total = len(scheduled_lessons)
    completed = sum(1 for item in scheduled_lessons if item["status"] == "completed")
    in_progress = sum(1 for item in scheduled_lessons if item["status"] == "in_progress")
    not_started = sum(1 for item in scheduled_lessons if item["status"] == "not_started")
    overdue = sum(1 for item in scheduled_lessons if item["status"] == "overdue")
    skipped = sum(1 for item in scheduled_lessons if item["status"] == "skipped")
    completion_percent = round((completed / total) * 100, 1) if total else 0.0
    expected_percent = _expected_progress_percent(metadata, today)

    units: dict[str, dict[str, Any]] = {}
    for item in scheduled_lessons:
        key = str(item["unit_id"] if item["unit_id"] is not None else item["unit_title_ar"] or "unknown")
        unit = units.setdefault(
            key,
            {
                "unit_id": item["unit_id"],
                "unit_title_ar": item["unit_title_ar"] or "بدون وحدة",
                "total_lessons": 0,
                "completed_lessons": 0,
            },
        )
        unit["total_lessons"] += 1
        if item["status"] == "completed":
            unit["completed_lessons"] += 1

    unit_progress = [
        {
            **unit,
            "completion_percent": round((unit["completed_lessons"] / unit["total_lessons"]) * 100, 1)
            if unit["total_lessons"]
            else 0.0,
        }
        for unit in units.values()
    ]

    next_lesson_item = next(
        (item for item in scheduled_lessons if item["status"] not in {"completed", "skipped"}),
        None,
    )
    next_lesson = (
        {
            "id": next_lesson_item["lesson_id"],
            "title_ar": next_lesson_item["lesson_title_ar"],
            "scheduled_date": next_lesson_item["scheduled_date"],
            "status": next_lesson_item["status"],
        }
        if next_lesson_item
        else None
    )

    return {
        "plan_id": plan.id,
        "plan_title": str(metadata.get("title") or "خطة الكيمياء"),
        "total_scheduled_lessons": total,
        "completed_lessons": completed,
        "in_progress_lessons": in_progress,
        "not_started_lessons": not_started,
        "overdue_lessons": overdue,
        "skipped_lessons": skipped,
        "completion_percent": completion_percent,
        "expected_percent": expected_percent,
        "track_status": _track_status(completion_percent, expected_percent),
        "next_lesson": next_lesson,
        "unit_progress": unit_progress,
        "scheduled_lessons": scheduled_lessons,
    }


async def generate_study_plan(db: AsyncSession, user_id: int, request: StudyPlanGenerateRequest) -> StudyPlan:
    start_date, end_date, exam_date = _validate_plan_dates(request)
    selected_ids = _lesson_ids(request.lessonIds)
    stmt = (
        select(Lesson)
        .options(selectinload(Lesson.chapter).selectinload(Chapter.unit))
        .where(Lesson.id.in_(selected_ids))
        .order_by(Lesson.chapter_id, Lesson.order, Lesson.id)
    )
    result = await db.execute(stmt)
    lessons = list(result.scalars().all())
    found_ids = {lesson.id for lesson in lessons}
    missing_ids = [lesson_id for lesson_id in selected_ids if lesson_id not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=422, detail=f"Selected lessons were not found: {missing_ids}")
    use_exam_defaults = bool(request.examDate)
    study_days = _normalize_study_days(request.studyDays, use_exam_defaults=use_exam_defaults)
    hours = _hours_by_day(request, study_days)
    schedule, schedule_summary = _build_schedule(
        lessons=lessons,
        start_date=start_date,
        end_date=end_date,
        study_days=study_days,
        hours=hours,
    )

    chapters: dict[int, dict[str, Any]] = {}
    for lesson in lessons:
        chapter_id = lesson.chapter_id
        unit = lesson.chapter.unit if lesson.chapter and lesson.chapter.unit else None
        if chapter_id not in chapters:
            chapters[chapter_id] = {
                "id": chapter_id,
                "unit_id": unit.id if unit else None,
                "unit_number": unit.unit_number if unit else None,
                "semester": unit.semester if unit else None,
                "title": lesson.chapter.title_ar if lesson.chapter else f"الفصل {chapter_id}",
                "subtitle": (
                    f"الوحدة {unit.unit_number} · {lesson.chapter.description_ar or lesson.chapter.title_ar}"
                    if unit and lesson.chapter
                    else lesson.chapter.description_ar if lesson.chapter else ""
                ),
                "progress": 0,
                "lessons": [],
            }
        chapters[chapter_id]["lessons"].append(
            {
                "id": lesson.id,
                "title": lesson.title_ar,
                "duration": lesson.duration_min,
                "status": "current" if not any(c["lessons"] for c in chapters.values() if c is not chapters[chapter_id]) and not chapters[chapter_id]["lessons"] else "locked",
            }
        )

    config = request.model_dump()
    config.update(
        {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "examDate": exam_date.isoformat() if exam_date else config.get("examDate"),
            "studyDays": study_days,
            "studyHoursByDay": hours,
        }
    )
    plan_json = {
        "title": request.title or "خطة دراسة الكيمياء",
        "overview": "خطة دراسة يومية مبنية على الدروس المختارة والوقت المتاح لكل يوم.",
        "target_date": end_date.isoformat(),
        "config": config,
        "chapters": list(chapters.values()),
        "lesson_ids": selected_ids,
        "completed_lesson_ids": [],
        "weakTopics": [],
        "weak_topics": [],
        "currentLesson": (list(chapters.values())[0]["lessons"][0] if chapters and list(chapters.values())[0]["lessons"] else None),
        "schedule": schedule,
        "weeks": _build_plan_weeks(schedule),
        "study_days": [{"code": day, "label": WEEKDAYS[day]["ar"]} for day in study_days],
        "recommendations": [
            "ابدأ بالدرس المجدول ثم راجع بطاقاته في نفس اليوم.",
            "استخدم الاختبار القصير بعد كل مجموعة دروس لتثبيت الفهم.",
        ],
        "summary": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "exam_date": exam_date.isoformat() if exam_date else None,
            "total_lessons": len(lessons),
            **schedule_summary,
        },
    }
    _validate_plan_json_contract(plan_json)
    plan = StudyPlan(user_id=user_id, exam_date=exam_date, status="active", plan_json=plan_json)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan

async def update_study_plan(db: AsyncSession, plan_id: int, user_id: int, request: StudyPlanUpdate) -> StudyPlan:
    plan = await get_study_plan(db, plan_id, user_id)
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    return plan


async def get_study_plan_progress(db: AsyncSession, plan_id: int, user_id: int) -> dict[str, Any]:
    plan = await get_study_plan(db, plan_id, user_id)
    metadata = plan.plan_json if isinstance(plan.plan_json, dict) else {}
    lesson_ids = _scheduled_lesson_ids(metadata)
    lessons_by_id: dict[int, Lesson] = {}
    progress_by_lesson_id: dict[int, LessonProgress] = {}

    if lesson_ids:
        lessons_result = await db.execute(
            select(Lesson)
            .options(selectinload(Lesson.chapter).selectinload(Chapter.unit))
            .where(Lesson.id.in_(lesson_ids))
        )
        lessons_by_id = {lesson.id: lesson for lesson in lessons_result.scalars().all()}

        progress_result = await db.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id.in_(lesson_ids),
            )
        )
        progress_by_lesson_id = {
            progress.lesson_id: progress for progress in progress_result.scalars().all()
        }

    return _build_study_plan_progress(
        plan=plan,
        lessons_by_id=lessons_by_id,
        progress_by_lesson_id=progress_by_lesson_id,
        today=_today(),
    )


def study_plan_lesson_ids(plan: StudyPlan) -> set[int]:
    """Return every lesson referenced by the persisted plan document."""

    metadata = plan.plan_json if isinstance(plan.plan_json, dict) else {}
    lesson_ids = set(_scheduled_lesson_ids(metadata))
    chapters = metadata.get("chapters") if isinstance(metadata.get("chapters"), list) else []
    for chapter in chapters:
        lessons = chapter.get("lessons") if isinstance(chapter, dict) else []
        if not isinstance(lessons, list):
            continue
        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            lesson_id = _as_int(lesson.get("id"))
            if lesson_id:
                lesson_ids.add(lesson_id)
    return lesson_ids


async def complete_study_plan_lesson(
    db: AsyncSession,
    plan_id: int,
    user_id: int,
    lesson_id: int,
    *,
    completed_at: datetime | None = None,
    commit: bool = True,
) -> StudyPlan:
    plan = await get_study_plan(db, plan_id, user_id)
    metadata = deepcopy(plan.plan_json) if isinstance(plan.plan_json, dict) else {}
    planned_lesson_ids = study_plan_lesson_ids(plan)
    chapters = metadata.get("chapters") if isinstance(metadata.get("chapters"), list) else []
    if planned_lesson_ids and int(lesson_id) not in planned_lesson_ids:
        raise HTTPException(status_code=422, detail="Lesson is not part of this study plan")

    completed = {int(item) for item in metadata.get("completed_lesson_ids", []) if str(item).isdigit()}
    completed.add(int(lesson_id))
    metadata["completed_lesson_ids"] = sorted(completed)

    next_current = None
    total = 0
    done = 0
    completed_at = completed_at or datetime.now(timezone.utc)
    for chapter in chapters:
        lessons = chapter.get("lessons") if isinstance(chapter, dict) else []
        if not isinstance(lessons, list):
            continue
        chapter_done = 0
        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            total += 1
            try:
                current_id = int(lesson.get("id"))
            except (TypeError, ValueError):
                current_id = -1
            if current_id in completed:
                lesson["status"] = "completed"
                done += 1
                chapter_done += 1
            elif next_current is None:
                lesson["status"] = "current"
                next_current = lesson
            elif lesson.get("status") != "completed":
                lesson["status"] = "locked"
        chapter["progress"] = round((chapter_done / len(lessons)) * 100) if lessons else 0
    metadata["currentLesson"] = next_current
    metadata["overall_progress"] = round((done / total) * 100) if total else 0
    schedule = metadata.get("schedule") if isinstance(metadata.get("schedule"), list) else []
    for entry in schedule:
        if not isinstance(entry, dict):
            continue
        sessions = entry.get("sessions") if isinstance(entry.get("sessions"), list) else []
        for session in sessions:
            if not isinstance(session, dict) or session.get("type") != "lesson":
                continue
            try:
                session_lesson_id = int(session.get("lesson_id"))
            except (TypeError, ValueError):
                continue
            if session_lesson_id in completed:
                session["completed"] = True
                session["status"] = "completed"
                session["completed_at"] = completed_at.isoformat()
    weeks = metadata.get("weeks") if isinstance(metadata.get("weeks"), list) else []
    for week in weeks:
        days = week.get("days") if isinstance(week, dict) else []
        if not isinstance(days, list):
            continue
        for day in days:
            tasks = day.get("tasks") if isinstance(day, dict) else []
            if not isinstance(tasks, list):
                continue
            for task in tasks:
                if not isinstance(task, dict) or task.get("type") != "lesson":
                    continue
                task_lesson_id = _as_int(task.get("lesson_id"))
                if task_lesson_id in completed:
                    task["status"] = "completed"
                    task["completed_at"] = completed_at.isoformat()
    plan.plan_json = metadata

    result = await db.execute(
        select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = LessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            status="completed",
            completed_at=completed_at,
        )
        db.add(progress)
    else:
        progress.status = "completed"
        progress.completed_at = completed_at

    if commit:
        await db.commit()
        await db.refresh(plan)
    else:
        await db.flush()
    return plan

async def delete_study_plan(db: AsyncSession, plan_id: int, user_id: int) -> None:
    plan = await get_study_plan(db, plan_id, user_id)
    await db.delete(plan)
    await db.commit()
