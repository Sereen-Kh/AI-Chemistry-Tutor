"""Exam practice API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.schemas.quiz import QuizGenerateResponse, QuizQuestionResponse
from app.services import quiz_service

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("/practice", response_model=QuizGenerateResponse)
async def exam_practice(db: AsyncSession = Depends(get_async_db)):
    questions, generated, source = await quiz_service.generate_quiz(db, topic_id=None, source_type="exam", limit=10)
    return QuizGenerateResponse(
        questions=[
            QuizQuestionResponse(
                id=question.id,
                lesson_id=question.lesson_id,
                topic_id=question.topic_id,
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                page_number=question.page_number,
                source_id=question.source_id,
                difficulty=question.difficulty,
            )
            for question in questions
        ],
        generated=generated,
        source=source,
    )
