"""Student profile API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.student_profile import StudentProfileResponse, StudentProfileUpsertRequest
from app.services.profile_service import get_or_create_profile, upsert_profile

router = APIRouter(prefix="/student-profile", tags=["student-profile"])


@router.get("/me", response_model=StudentProfileResponse)
async def get_my_profile(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_async_db)):
    return await get_or_create_profile(db, user_id)


@router.put("/me", response_model=StudentProfileResponse)
async def upsert_my_profile(
    request: StudentProfileUpsertRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await upsert_profile(db, user_id, request.model_dump())
