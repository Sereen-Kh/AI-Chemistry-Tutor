from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.schemas.elements import ElementResponse
from app.services import element_service
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/elements", tags=["elements"])

@router.get("", response_model=list[ElementResponse])
async def list_elements(
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    return await element_service.get_elements(db)

@router.get("/{atomic_number}", response_model=ElementResponse)
async def get_element(
    atomic_number: int,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    return await element_service.get_element(db, atomic_number)
