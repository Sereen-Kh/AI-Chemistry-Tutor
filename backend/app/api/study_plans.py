from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.schemas.study_plans import (
    StudyPlanCreate,
    StudyPlanGenerateRequest,
    StudyPlanProgressResponse,
    StudyPlanResponse,
    StudyPlanUpdate,
)
from app.services import study_plan_service
from app.core.dependencies import get_current_user_id

router = APIRouter(prefix="/study-plans", tags=["study_plans"])

@router.get("", response_model=list[StudyPlanResponse])
async def list_study_plans(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_plan_service.get_study_plans(db, user_id)

@router.post("/generate", response_model=StudyPlanResponse, status_code=201)
async def generate_study_plan(
    request: StudyPlanGenerateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_plan_service.generate_study_plan(db, user_id, request)

@router.get("/{plan_id}", response_model=StudyPlanResponse)
async def get_study_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_plan_service.get_study_plan(db, plan_id, user_id)


@router.get("/{plan_id}/progress", response_model=StudyPlanProgressResponse)
async def get_study_plan_progress(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_plan_service.get_study_plan_progress(db, plan_id, user_id)

@router.post("", response_model=StudyPlanResponse, status_code=201)
async def create_study_plan(
    request: StudyPlanCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_plan_service.create_study_plan(db, user_id, request)

@router.put("/{plan_id}", response_model=StudyPlanResponse)
async def update_study_plan(
    plan_id: int,
    request: StudyPlanUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_plan_service.update_study_plan(db, plan_id, user_id, request)

@router.post("/{plan_id}/lessons/{lesson_id}/complete", response_model=StudyPlanResponse)
async def complete_study_plan_lesson(
    plan_id: int,
    lesson_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await study_plan_service.complete_study_plan_lesson(db, plan_id, user_id, lesson_id)

@router.delete("/{plan_id}", status_code=204)
async def delete_study_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await study_plan_service.delete_study_plan(db, plan_id, user_id)
    return Response(status_code=204)
