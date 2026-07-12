"""Homework solver service functions."""

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.homework import Homework
from app.services import ai_service
from app.services.rag import retrieve_context, format_context
from app.services.ocr import get_vision_provider


_INSUFFICIENT_CONTEXT = "لم أجد معلومات كافية في المصادر التعليمية المراجعة لحل هذه المسألة بثقة."


def _source_citation(chunk) -> dict:
    metadata = chunk.curriculum_metadata if isinstance(chunk.curriculum_metadata, dict) else {}
    if not metadata and isinstance(chunk.metadata_json, dict):
        metadata = chunk.metadata_json
    return {
        "chunk_id": chunk.id,
        "source_id": chunk.source_id,
        "source_type": chunk.source_type,
        "page_number": chunk.page_number,
        "printed_page_start": metadata.get("printed_page_start") or chunk.page_number,
        "printed_page_end": metadata.get("printed_page_end") or chunk.page_number,
        "unit_id": chunk.unit_id or metadata.get("unit_id"),
        "lesson_id": chunk.lesson_id or metadata.get("lesson_id"),
        "content_type": chunk.content_type,
        "similarity_score": round(float(chunk.similarity_score), 4),
        "quality_status": chunk.quality_status or metadata.get("quality_status"),
        "quality_warning": chunk.quality_warning,
        "reviewed_metadata_version": chunk.reviewed_metadata_version
        or metadata.get("reviewed_metadata_version"),
    }


async def solve_text(db: AsyncSession, user_id: int, problem_text: str, topic_id: int | None = None) -> Homework:
    chunks = await retrieve_context(db, problem_text, user_id=user_id, topic_id=topic_id, top_k=5)
    context = format_context(chunks)
    citations = [_source_citation(chunk) for chunk in chunks]

    if not context:
        item = Homework(
            user_id=user_id,
            topic_id=topic_id,
            problem_text=problem_text,
            solution=_INSUFFICIENT_CONTEXT,
            source_chunks=[],
            confidence_score=0.0,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    system_prompt = "قم بحل هذه المسألة الكيميائية. اشرح خطوات الحل."
    system_prompt += f"\nاستخدم المصادر التالية للمساعدة إذا لزم الأمر:\n\n{context}"

    answer = await ai_service.get_ai_response([{"role": "user", "content": problem_text}], system_prompt=system_prompt)
    confidence = max((float(chunk.similarity_score) for chunk in chunks), default=0.0)
    item = Homework(
        user_id=user_id,
        topic_id=topic_id,
        problem_text=problem_text,
        solution=answer,
        source_chunks=citations,
        confidence_score=round(confidence, 4),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def solve_image(db: AsyncSession, user_id: int, image_path: str, topic_id: int | None = None) -> Homework:
    path = Path(image_path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    provider = get_vision_provider("gemini")
    if not provider.is_configured:
        raise HTTPException(status_code=503, detail="Gemini document extraction is not configured")
    extraction = await provider.extract_page(str(path), page_number=1, source_type="homework")
    extracted_text = "\n\n".join(section.content for section in extraction.sections)
    item = await solve_text(db, user_id, extracted_text or "حل مسألة من صورة", topic_id=topic_id)
    item.image_url = str(path)
    item.extracted_text = extracted_text
    await db.commit()
    await db.refresh(item)
    return item


async def list_homework(db: AsyncSession, user_id: int) -> list[Homework]:
    result = await db.execute(select(Homework).where(Homework.user_id == user_id).order_by(desc(Homework.created_at)))
    return list(result.scalars().all())


async def get_homework(db: AsyncSession, user_id: int, homework_id: int) -> Homework:
    item = await db.get(Homework, homework_id)
    if item is None or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Homework item not found")
    return item
