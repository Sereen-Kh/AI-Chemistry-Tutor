"""Quiz and exam trainer API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.database import get_async_db
from app.schemas.quiz import (
    QuizAttemptResponse,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizQuestionResponse,
    QuizRecommendationResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services import quiz_service

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(request: QuizGenerateRequest, db: AsyncSession = Depends(get_async_db)):
    questions = await quiz_service.generate_quiz(
        db,
        topic_id=request.topic_id,
        lesson_id=request.lesson_id,
        source_type=request.source_type,
        limit=request.limit,
    )
    return QuizGenerateResponse(
        questions=[
            QuizQuestionResponse(
                id=question.id,
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                page_number=question.page_number,
                source_id=question.source_id,
                difficulty=question.difficulty,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )
            for question in questions
        ]
    )


@router.post("/submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    attempt = await quiz_service.submit_quiz(db, user_id, request.topic_id, request.answers)
    return QuizSubmitResponse(
        attempt_id=attempt.id,
        score=attempt.score,
        total=attempt.total,
        weak_topics=attempt.weak_topics,
        percentage=round((attempt.score / attempt.total) * 100, 2) if attempt.total else 0.0,
    )


@router.get("/history", response_model=list[QuizAttemptResponse])
async def quiz_history(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_async_db)):
    return await quiz_service.list_attempts(db, user_id)


@router.get("/recommendations", response_model=list[QuizRecommendationResponse])
async def quiz_recommendations(db: AsyncSession = Depends(get_async_db)):
    return await quiz_service.recommendations(db)
