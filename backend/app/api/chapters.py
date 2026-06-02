"""Chapter API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.database import get_async_db
from app.schemas.chapters import ChapterCreateRequest, ChapterResponse, ChapterUpdateRequest
from app.services import curriculum_service

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("", response_model=list[ChapterResponse])
async def list_chapters(db: AsyncSession = Depends(get_async_db)):
    return await curriculum_service.list_chapters(db)


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(chapter_id: int, db: AsyncSession = Depends(get_async_db)):
    return await curriculum_service.get_chapter(db, chapter_id)


@router.post("", response_model=ChapterResponse, status_code=201)
async def create_chapter(
    request: ChapterCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    return await curriculum_service.create_chapter(db, request.model_dump())


@router.patch("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    request: ChapterUpdateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    return await curriculum_service.update_chapter(db, chapter_id, request.model_dump(exclude_unset=True))
