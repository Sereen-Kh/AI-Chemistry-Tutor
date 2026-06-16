from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chemistry import Chapter, Lesson, LessonProgress
from app.models.study_plan import StudyPlan
from app.schemas.study_plans import StudyPlanCreate, StudyPlanGenerateRequest, StudyPlanUpdate

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


def _lesson_ids(raw: list[str | int]) -> list[int]:
    ids: list[int] = []
    for item in raw:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


async def generate_study_plan(db: AsyncSession, user_id: int, request: StudyPlanGenerateRequest) -> StudyPlan:
    selected_ids = _lesson_ids(request.lessonIds)
    stmt = (
        select(Lesson)
        .options(selectinload(Lesson.chapter).selectinload(Chapter.unit))
        .order_by(Lesson.chapter_id, Lesson.order, Lesson.id)
    )
    if selected_ids:
        stmt = stmt.where(Lesson.id.in_(selected_ids))
    result = await db.execute(stmt)
    lessons = list(result.scalars().all())

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

    exam_date = _parse_date(request.examDate) or _parse_date(request.endDate)
    plan_json = {
        "title": request.title or "خطة دراسة الكيمياء",
        "config": request.model_dump(),
        "chapters": list(chapters.values()),
        "lesson_ids": selected_ids,
        "completed_lesson_ids": [],
        "weakTopics": [],
        "currentLesson": (list(chapters.values())[0]["lessons"][0] if chapters and list(chapters.values())[0]["lessons"] else None),
    }
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


async def complete_study_plan_lesson(db: AsyncSession, plan_id: int, user_id: int, lesson_id: int) -> StudyPlan:
    plan = await get_study_plan(db, plan_id, user_id)
    metadata = plan.plan_json if isinstance(plan.plan_json, dict) else {}
    completed = {int(item) for item in metadata.get("completed_lesson_ids", []) if str(item).isdigit()}
    completed.add(int(lesson_id))
    metadata["completed_lesson_ids"] = sorted(completed)

    chapters = metadata.get("chapters") if isinstance(metadata.get("chapters"), list) else []
    next_current = None
    total = 0
    done = 0
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
    plan.plan_json = metadata

    result = await db.execute(
        select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = LessonProgress(user_id=user_id, lesson_id=lesson_id, status="completed")
        db.add(progress)
    else:
        progress.status = "completed"

    await db.commit()
    await db.refresh(plan)
    return plan

async def delete_study_plan(db: AsyncSession, plan_id: int, user_id: int) -> None:
    plan = await get_study_plan(db, plan_id, user_id)
    await db.delete(plan)
    await db.commit()
