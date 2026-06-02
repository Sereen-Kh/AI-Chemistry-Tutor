from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.schemas.topics import TopicCreate, TopicResponse, TopicUpdate
from app.services import topic_service
from app.core.dependencies import require_admin, get_current_user

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("", response_model=list[TopicResponse])
async def list_topics(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    return await topic_service.get_topics(db, skip=skip, limit=limit)

@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    return await topic_service.get_topic(db, topic_id)

@router.post("", response_model=TopicResponse, status_code=201)
async def create_topic(
    request: TopicCreate,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin),
):
    return await topic_service.create_topic(db, request)

@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: int,
    request: TopicUpdate,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin),
):
    return await topic_service.update_topic(db, topic_id, request)

@router.delete("/{topic_id}", status_code=204)
async def delete_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin),
):
    await topic_service.delete_topic(db, topic_id)
    return Response(status_code=204)
