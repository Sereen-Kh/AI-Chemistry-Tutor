from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.study_plan import StudyPlan
from app.schemas.study_plans import StudyPlanCreate, StudyPlanUpdate

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

async def update_study_plan(db: AsyncSession, plan_id: int, user_id: int, request: StudyPlanUpdate) -> StudyPlan:
    plan = await get_study_plan(db, plan_id, user_id)
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    return plan

async def delete_study_plan(db: AsyncSession, plan_id: int, user_id: int) -> None:
    plan = await get_study_plan(db, plan_id, user_id)
    await db.delete(plan)
    await db.commit()
