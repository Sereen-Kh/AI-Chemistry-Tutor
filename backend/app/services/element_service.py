from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chemistry import Element

async def get_elements(db: AsyncSession) -> list[Element]:
    result = await db.execute(select(Element).order_by(Element.atomic_number.asc()))
    return list(result.scalars().all())

async def get_element(db: AsyncSession, atomic_number: int) -> Element:
    element = await db.get(Element, atomic_number)
    if not element:
        raise HTTPException(status_code=404, detail="Element not found")
    return element
