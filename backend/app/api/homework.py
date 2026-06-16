"""Homework solver API routes."""

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_DIR
from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.models.homework import Homework
from app.schemas.homework import (
    HomeworkResponse,
    HomeworkSolveImageRequest,
    HomeworkSolveTextRequest,
    HomeworkUploadResponse,
)
from app.services import homework_service

router = APIRouter(prefix="/homework", tags=["homework"])

_ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_MAX_UPLOAD_BYTES = 8 * 1024 * 1024


@router.post("/solve-text", response_model=HomeworkResponse)
async def solve_text(
    request: HomeworkSolveTextRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await homework_service.solve_text(db, user_id, request.problem_text, request.topic_id)


@router.post("/upload", response_model=HomeworkUploadResponse, status_code=201)
async def upload_homework_image(
    file: UploadFile = File(...),
    topic_id: int | None = Form(default=None),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Store a homework image from web/mobile clients and create a placeholder record.

    The existing image solver works from a server-side path. This endpoint gives
    browser/mobile clients a standard multipart upload flow and returns the path
    that can be passed to ``/homework/solve-image``.
    """
    extension = _ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP homework images are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(payload) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Homework image is too large. Maximum size is 8 MB.")

    upload_dir = PROJECT_DIR / "data" / "uploads" / "homework" / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}{extension}"
    target = upload_dir / safe_name
    target.write_bytes(payload)

    relative_url = f"/media/uploads/homework/{user_id}/{safe_name}"
    item = Homework(
        user_id=user_id,
        topic_id=topic_id,
        image_url=relative_url,
        problem_text="صورة واجب مرفوعة بانتظار الحل",
        solution="",
        confidence_score=None,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return HomeworkUploadResponse(
        homework_id=item.id,
        image_url=relative_url,
        image_path=str(target),
        filename=file.filename or safe_name,
        content_type=file.content_type,
    )


@router.post("/solve-image", response_model=HomeworkResponse)
async def solve_image(
    request: HomeworkSolveImageRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await homework_service.solve_image(db, user_id, request.image_path, request.topic_id)


@router.get("/history", response_model=list[HomeworkResponse])
async def homework_history(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_async_db)):
    return await homework_service.list_homework(db, user_id)


@router.get("/{homework_id}", response_model=HomeworkResponse)
async def get_homework(
    homework_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    return await homework_service.get_homework(db, user_id, homework_id)
