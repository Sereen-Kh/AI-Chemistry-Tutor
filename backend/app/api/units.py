"""Textbook unit API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.schemas.chapters import ChapterResponse
from app.schemas.units import UnitCatalogResponse
from app.services import curriculum_service

router = APIRouter(prefix="/units", tags=["units"])


@router.get("", response_model=list[UnitCatalogResponse])
async def list_units(
    semester: int | None = Query(default=None, ge=1, le=2),
    db: AsyncSession = Depends(get_async_db),
):
    return await curriculum_service.list_units(db, semester=semester)


@router.get("/{unit_id}", response_model=UnitCatalogResponse)
async def get_unit(unit_id: int, db: AsyncSession = Depends(get_async_db)):
    return await curriculum_service.get_unit(db, unit_id)


@router.get("/{unit_id}/chapters", response_model=list[ChapterResponse])
async def list_unit_chapters(unit_id: int, db: AsyncSession = Depends(get_async_db)):
    return await curriculum_service.list_unit_chapters(db, unit_id)
