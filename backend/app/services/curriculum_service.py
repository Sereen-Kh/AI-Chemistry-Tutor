"""Curriculum service functions."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chemistry import Chapter, Lesson, Unit


async def list_units(db: AsyncSession, semester: int | None = None) -> list[Unit]:
    stmt = select(Unit).options(
        selectinload(Unit.chapters).selectinload(Chapter.lessons).selectinload(Lesson.topics)
    )
    if semester is not None:
        stmt = stmt.where(Unit.semester == semester)
    result = await db.execute(stmt.order_by(Unit.semester, Unit.order, Unit.id))
    return list(result.unique().scalars().all())


async def get_unit(db: AsyncSession, unit_id: int) -> Unit:
    result = await db.execute(
        select(Unit)
        .where(Unit.id == unit_id)
        .options(selectinload(Unit.chapters).selectinload(Chapter.lessons).selectinload(Lesson.topics))
    )
    unit = result.unique().scalar_one_or_none()
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


async def list_unit_chapters(db: AsyncSession, unit_id: int) -> list[Chapter]:
    await get_unit(db, unit_id)
    result = await db.execute(
        select(Chapter)
        .where(Chapter.unit_id == unit_id)
        .options(selectinload(Chapter.lessons).selectinload(Lesson.topics))
        .order_by(Chapter.order, Chapter.id)
    )
    return list(result.unique().scalars().all())


async def list_chapters(
    db: AsyncSession,
    semester: int | None = None,
    unit_id: int | None = None,
) -> list[Chapter]:
    stmt = select(Chapter).options(selectinload(Chapter.lessons).selectinload(Lesson.topics))
    if unit_id is not None:
        stmt = stmt.where(Chapter.unit_id == unit_id)
    if semester is not None:
        stmt = stmt.join(Unit, Chapter.unit_id == Unit.id).where(Unit.semester == semester)
    result = await db.execute(stmt.order_by(Chapter.order, Chapter.id))
    return list(result.unique().scalars().all())


async def get_chapter(db: AsyncSession, chapter_id: int) -> Chapter:
    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


async def create_chapter(db: AsyncSession, data: dict) -> Chapter:
    if data.get("unit_id") is not None:
        await get_unit(db, data["unit_id"])
    chapter = Chapter(**data)
    db.add(chapter)
    await db.commit()
    await db.refresh(chapter)
    return chapter


async def update_chapter(db: AsyncSession, chapter_id: int, data: dict) -> Chapter:
    chapter = await get_chapter(db, chapter_id)
    if data.get("unit_id") is not None:
        await get_unit(db, data["unit_id"])
    for field, value in data.items():
        if value is not None:
            setattr(chapter, field, value)
    await db.commit()
    await db.refresh(chapter)
    return chapter


async def list_lessons(
    db: AsyncSession,
    chapter_id: int | None = None,
    semester: int | None = None,
) -> list[Lesson]:
    stmt = select(Lesson).options(selectinload(Lesson.topics), selectinload(Lesson.chapter).selectinload(Chapter.unit))
    if chapter_id is not None:
        stmt = stmt.where(Lesson.chapter_id == chapter_id)
    if semester is not None:
        stmt = stmt.join(Chapter, Lesson.chapter_id == Chapter.id).join(Unit, Chapter.unit_id == Unit.id)
        stmt = stmt.where(Unit.semester == semester)
    result = await db.execute(stmt.order_by(Lesson.chapter_id, Lesson.order, Lesson.id))
    return list(result.unique().scalars().all())


async def get_lesson(db: AsyncSession, lesson_id: int) -> Lesson:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.topics), selectinload(Lesson.chapter).selectinload(Chapter.unit))
    )
    lesson = result.unique().scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


async def create_lesson(db: AsyncSession, data: dict) -> Lesson:
    await get_chapter(db, data["chapter_id"])
    lesson = Lesson(**data)
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def update_lesson(db: AsyncSession, lesson_id: int, data: dict) -> Lesson:
    lesson = await get_lesson(db, lesson_id)
    for field, value in data.items():
        if value is not None:
            setattr(lesson, field, value)
    await db.commit()
    await db.refresh(lesson)
    return lesson
