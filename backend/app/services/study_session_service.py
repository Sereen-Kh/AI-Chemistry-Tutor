"""Persistent Study Session lifecycle and elapsed-time accounting."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chemistry import Lesson, LessonProgress
from app.models.study_plan import StudyPlan
from app.models.study_session import StudySession
from app.models.user import User
from app.schemas.study_sessions import StudySessionCreate
from app.services import study_plan_service


HEARTBEAT_INTERVAL_SECONDS = 30
STALE_AFTER_SECONDS = 90
MAX_SESSION_SECONDS = 4 * 60 * 60
OPEN_STATUSES = ("running", "paused")
TERMINAL_STATUSES = ("completed", "abandoned")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _elapsed_delta(start: datetime, end: datetime) -> int:
    return max(0, int((_aware(end) - _aware(start)).total_seconds()))


def _effective_elapsed(session: StudySession, now: datetime) -> int:
    elapsed = int(session.elapsed_seconds or 0)
    if session.status == "running":
        elapsed += min(_elapsed_delta(session.last_heartbeat_at, now), STALE_AFTER_SECONDS)
    return min(elapsed, MAX_SESSION_SECONDS)


def _accrue_running(session: StudySession, now: datetime) -> bool:
    """Persist a running interval and pause when its heartbeat is stale."""

    if session.status != "running":
        return False
    delta = _elapsed_delta(session.last_heartbeat_at, now)
    credited = min(delta, STALE_AFTER_SECONDS)
    session.elapsed_seconds = min(int(session.elapsed_seconds or 0) + credited, MAX_SESSION_SECONDS)
    if delta > STALE_AFTER_SECONDS:
        cutoff = _aware(session.last_heartbeat_at) + timedelta(seconds=STALE_AFTER_SECONDS)
        session.last_heartbeat_at = cutoff
        session.status = "paused"
        session.paused_at = cutoff
        return True
    session.last_heartbeat_at = now
    return False


def _pause_running(session: StudySession, now: datetime) -> bool:
    if session.status != "running":
        return False
    stale = _accrue_running(session, now)
    if not stale:
        session.status = "paused"
        session.paused_at = now
    return stale


def _session_query():
    return select(StudySession).options(selectinload(StudySession.lesson))


async def _owned_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    *,
    for_update: bool = False,
) -> StudySession:
    statement = _session_query().where(
        StudySession.id == session_id,
        StudySession.user_id == user_id,
    )
    if for_update:
        statement = statement.with_for_update()
    session = (await db.execute(statement)).scalar_one_or_none()
    if session is None:
        raise _error(404, "STUDY_SESSION_NOT_FOUND", "لم يتم العثور على جلسة الدراسة.")
    return session


async def _reload(db: AsyncSession, session_id: int) -> StudySession:
    session = (await db.execute(_session_query().where(StudySession.id == session_id))).scalar_one()
    return session


def _response(
    session: StudySession,
    now: datetime,
    *,
    lesson_progress_updated: bool = False,
    study_plan_updated: bool = False,
    stale_reconciled: bool = False,
) -> dict:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "lesson_id": session.lesson_id,
        "study_plan_id": session.study_plan_id,
        "status": session.status,
        "planned_minutes": session.planned_minutes,
        "elapsed_seconds": _effective_elapsed(session, now),
        "started_at": session.started_at,
        "last_heartbeat_at": session.last_heartbeat_at,
        "paused_at": session.paused_at,
        "completed_at": session.completed_at,
        "abandoned_at": session.abandoned_at,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "server_time": now,
        "lesson_title_ar": session.lesson.title_ar,
        "lesson_page_start": session.lesson.page_start,
        "lesson_page_end": session.lesson.page_end,
        "lesson_progress_updated": lesson_progress_updated,
        "study_plan_updated": study_plan_updated,
        "stale_reconciled": stale_reconciled,
    }


async def _lock_user(db: AsyncSession, user_id: int) -> None:
    exists = await db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    if exists is None:
        raise _error(404, "USER_NOT_FOUND", "لم يتم العثور على المستخدم.")


async def _validate_lesson(db: AsyncSession, lesson_id: int) -> Lesson:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise _error(404, "LESSON_NOT_FOUND", "لم يتم العثور على الدرس داخل المنهج.")
    return lesson


async def _validate_plan(
    db: AsyncSession,
    user_id: int,
    plan_id: int,
    lesson_id: int,
) -> StudyPlan:
    plan = await db.get(StudyPlan, plan_id)
    if plan is None or plan.user_id != user_id:
        raise _error(404, "STUDY_PLAN_NOT_FOUND", "لم يتم العثور على خطة الدراسة.")
    if lesson_id not in study_plan_service.study_plan_lesson_ids(plan):
        raise _error(422, "LESSON_NOT_IN_STUDY_PLAN", "هذا الدرس غير موجود في خطة الدراسة المحددة.")
    return plan


def _planned_minutes(lesson: Lesson, plan: StudyPlan | None) -> int:
    if plan and isinstance(plan.plan_json, dict):
        schedule = plan.plan_json.get("schedule")
        if isinstance(schedule, list):
            total = 0
            for entry in schedule:
                sessions = entry.get("sessions") if isinstance(entry, dict) else None
                if not isinstance(sessions, list):
                    continue
                for item in sessions:
                    if not isinstance(item, dict) or item.get("type") != "lesson":
                        continue
                    try:
                        item_lesson_id = int(item.get("lesson_id"))
                    except (TypeError, ValueError):
                        continue
                    if item_lesson_id == lesson.id:
                        total += max(0, int(item.get("minutes") or 0))
            if total:
                return min(total, 8 * 60)
    return max(1, int(lesson.duration_min or 45))


async def _pause_other_running(
    db: AsyncSession,
    user_id: int,
    now: datetime,
    *,
    exclude_id: int | None = None,
) -> None:
    statement = select(StudySession).where(
        StudySession.user_id == user_id,
        StudySession.status == "running",
    )
    if exclude_id is not None:
        statement = statement.where(StudySession.id != exclude_id)
    sessions = list((await db.execute(statement.with_for_update())).scalars().all())
    for session in sessions:
        _pause_running(session, now)


async def start_study_session(
    db: AsyncSession,
    user_id: int,
    request: StudySessionCreate,
    *,
    now: datetime | None = None,
) -> dict:
    current_time = now or _now()
    await _lock_user(db, user_id)
    lesson = await _validate_lesson(db, request.lesson_id)
    plan = None
    if request.study_plan_id is not None:
        plan = await _validate_plan(db, user_id, request.study_plan_id, request.lesson_id)

    existing = await db.scalar(
        _session_query()
        .where(
            StudySession.user_id == user_id,
            StudySession.lesson_id == request.lesson_id,
            StudySession.status.in_(OPEN_STATUSES),
        )
        .order_by(StudySession.created_at.desc())
        .with_for_update()
    )
    if existing is not None:
        stale = _accrue_running(existing, current_time)
        if stale:
            await db.commit()
            existing = await _reload(db, existing.id)
        return _response(existing, current_time, stale_reconciled=stale)

    await _pause_other_running(db, user_id, current_time)
    session = StudySession(
        user_id=user_id,
        lesson_id=lesson.id,
        study_plan_id=plan.id if plan else None,
        status="running",
        planned_minutes=_planned_minutes(lesson, plan),
        elapsed_seconds=0,
        started_at=current_time,
        last_heartbeat_at=current_time,
    )
    db.add(session)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            _session_query().where(
                StudySession.user_id == user_id,
                StudySession.lesson_id == request.lesson_id,
                StudySession.status.in_(OPEN_STATUSES),
            )
        )
        if existing is None:
            raise
        return _response(existing, current_time)
    session = await _reload(db, session.id)
    return _response(session, current_time)


async def get_current_session(
    db: AsyncSession,
    user_id: int,
    *,
    lesson_id: int | None = None,
    now: datetime | None = None,
) -> dict | None:
    current_time = now or _now()
    statement = _session_query().where(
        StudySession.user_id == user_id,
        StudySession.status.in_(OPEN_STATUSES),
    )
    if lesson_id is not None:
        statement = statement.where(StudySession.lesson_id == lesson_id)
    statement = statement.order_by(
        case((StudySession.status == "running", 0), else_=1),
        StudySession.updated_at.desc(),
    )
    session = (await db.execute(statement)).scalars().first()
    if session is None:
        return None
    stale = _accrue_running(session, current_time)
    if stale:
        await db.commit()
        session = await _reload(db, session.id)
    return _response(session, current_time, stale_reconciled=stale)


async def list_study_sessions(
    db: AsyncSession,
    user_id: int,
    *,
    status: str | None = None,
    lesson_id: int | None = None,
    limit: int = 20,
    now: datetime | None = None,
) -> list[dict]:
    current_time = now or _now()
    statement = _session_query().where(StudySession.user_id == user_id)
    if status:
        statement = statement.where(StudySession.status == status)
    if lesson_id is not None:
        statement = statement.where(StudySession.lesson_id == lesson_id)
    sessions = list(
        (await db.execute(statement.order_by(StudySession.created_at.desc()).limit(limit))).scalars().all()
    )
    stale_ids = {session.id for session in sessions if _accrue_running(session, current_time)}
    if stale_ids:
        await db.commit()
        sessions = [await _reload(db, session.id) for session in sessions]
    return [
        _response(session, current_time, stale_reconciled=session.id in stale_ids)
        for session in sessions
    ]


async def get_study_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    *,
    now: datetime | None = None,
) -> dict:
    current_time = now or _now()
    session = await _owned_session(db, user_id, session_id)
    stale = _accrue_running(session, current_time)
    if stale:
        await db.commit()
        session = await _reload(db, session.id)
    return _response(session, current_time, stale_reconciled=stale)


async def heartbeat_study_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    *,
    now: datetime | None = None,
) -> dict:
    current_time = now or _now()
    session = await _owned_session(db, user_id, session_id, for_update=True)
    if session.status in TERMINAL_STATUSES:
        raise _error(409, "STUDY_SESSION_ALREADY_FINISHED", "انتهت جلسة الدراسة بالفعل.")
    if session.status != "running":
        raise _error(409, "STUDY_SESSION_INVALID_TRANSITION", "يجب استئناف الجلسة قبل حفظ الوقت.")
    stale = _accrue_running(session, current_time)
    await db.commit()
    session = await _reload(db, session.id)
    return _response(session, current_time, stale_reconciled=stale)


async def pause_study_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    *,
    now: datetime | None = None,
) -> dict:
    current_time = now or _now()
    session = await _owned_session(db, user_id, session_id, for_update=True)
    if session.status in TERMINAL_STATUSES:
        raise _error(409, "STUDY_SESSION_ALREADY_FINISHED", "انتهت جلسة الدراسة بالفعل.")
    stale = _pause_running(session, current_time)
    await db.commit()
    session = await _reload(db, session.id)
    return _response(session, current_time, stale_reconciled=stale)


async def resume_study_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    *,
    now: datetime | None = None,
) -> dict:
    current_time = now or _now()
    await _lock_user(db, user_id)
    session = await _owned_session(db, user_id, session_id, for_update=True)
    if session.status in TERMINAL_STATUSES:
        raise _error(409, "STUDY_SESSION_ALREADY_FINISHED", "انتهت جلسة الدراسة بالفعل.")
    if session.status == "running":
        return _response(session, current_time)
    await _pause_other_running(db, user_id, current_time, exclude_id=session.id)
    session.status = "running"
    session.last_heartbeat_at = current_time
    session.paused_at = None
    await db.commit()
    session = await _reload(db, session.id)
    return _response(session, current_time)


async def _complete_lesson_progress(
    db: AsyncSession,
    user_id: int,
    lesson_id: int,
    completed_at: datetime,
) -> None:
    progress = await db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
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


async def complete_study_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    *,
    now: datetime | None = None,
) -> dict:
    current_time = now or _now()
    session = await _owned_session(db, user_id, session_id, for_update=True)
    if session.status == "completed":
        return _response(
            session,
            current_time,
            lesson_progress_updated=True,
            study_plan_updated=session.study_plan_id is not None,
        )
    if session.status == "abandoned":
        raise _error(409, "STUDY_SESSION_ALREADY_FINISHED", "تم إنهاء هذه الجلسة دون إكمال الدرس.")
    _pause_running(session, current_time)
    session.status = "completed"
    session.completed_at = current_time
    session.paused_at = None

    study_plan_updated = False
    if session.study_plan_id is not None:
        await study_plan_service.complete_study_plan_lesson(
            db,
            session.study_plan_id,
            user_id,
            session.lesson_id,
            completed_at=current_time,
            commit=False,
        )
        study_plan_updated = True
    else:
        await _complete_lesson_progress(db, user_id, session.lesson_id, current_time)

    await db.commit()
    session = await _reload(db, session.id)
    return _response(
        session,
        current_time,
        lesson_progress_updated=True,
        study_plan_updated=study_plan_updated,
    )


async def abandon_study_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    *,
    now: datetime | None = None,
) -> dict:
    current_time = now or _now()
    session = await _owned_session(db, user_id, session_id, for_update=True)
    if session.status == "abandoned":
        return _response(session, current_time)
    if session.status == "completed":
        raise _error(409, "STUDY_SESSION_ALREADY_FINISHED", "اكتملت جلسة الدراسة بالفعل.")
    _pause_running(session, current_time)
    session.status = "abandoned"
    session.abandoned_at = current_time
    session.paused_at = None
    await db.commit()
    session = await _reload(db, session.id)
    return _response(session, current_time)
