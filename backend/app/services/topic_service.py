from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chemistry import Lesson
from app.models.topic import Topic
from app.schemas.topics import TopicCreate, TopicUpdate

async def get_topics(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    lesson_id: int | None = None,
) -> list[Topic]:
    stmt = select(Topic).options(selectinload(Topic.lessons))
    if lesson_id is not None:
        stmt = stmt.join(Topic.lessons).where(Lesson.id == lesson_id)
    result = await db.execute(stmt.order_by(Topic.order.asc(), Topic.id.asc()).offset(skip).limit(limit))
    return list(result.unique().scalars().all())

async def get_topic(db: AsyncSession, topic_id: int) -> Topic:
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic

async def create_topic(db: AsyncSession, request: TopicCreate) -> Topic:
    topic = Topic(**request.model_dump())
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic

async def update_topic(db: AsyncSession, topic_id: int, request: TopicUpdate) -> Topic:
    topic = await get_topic(db, topic_id)
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(topic, key, value)
    await db.commit()
    await db.refresh(topic)
    return topic

async def delete_topic(db: AsyncSession, topic_id: int) -> None:
    topic = await get_topic(db, topic_id)
    await db.delete(topic)
    await db.commit()
