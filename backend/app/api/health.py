"""Health and readiness endpoints."""

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", service="edumind-backend", version="1.0.0")
