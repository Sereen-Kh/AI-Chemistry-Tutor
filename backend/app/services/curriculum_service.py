"""Curriculum service functions."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chemistry import Chapter, Lesson


async def list_chapters(db: AsyncSession) -> list[Chapter]:
    result = await db.execute(select(Chapter).order_by(Chapter.order, Chapter.id))
    return list(result.scalars().all())


async def get_chapter(db: AsyncSession, chapter_id: int) -> Chapter:
    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


async def create_chapter(db: AsyncSession, data: dict) -> Chapter:
    chapter = Chapter(**data)
    db.add(chapter)
    await db.commit()
    await db.refresh(chapter)
    return chapter


async def update_chapter(db: AsyncSession, chapter_id: int, data: dict) -> Chapter:
    chapter = await get_chapter(db, chapter_id)
    for field, value in data.items():
        if value is not None:
            setattr(chapter, field, value)
    await db.commit()
    await db.refresh(chapter)
    return chapter


async def list_lessons(db: AsyncSession, chapter_id: int | None = None) -> list[Lesson]:
    stmt = select(Lesson)
    if chapter_id is not None:
        stmt = stmt.where(Lesson.chapter_id == chapter_id)
    result = await db.execute(stmt.order_by(Lesson.chapter_id, Lesson.order, Lesson.id))
    return list(result.scalars().all())


async def get_lesson(db: AsyncSession, lesson_id: int) -> Lesson:
    lesson = await db.get(Lesson, lesson_id)
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
