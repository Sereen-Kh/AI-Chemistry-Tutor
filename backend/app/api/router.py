"""API v1 router."""

from fastapi import APIRouter

from app.api.chapters import router as chapters_router
from app.api.auth.routes import router as auth_router
from app.api.chat.routes import router as chat_router
from app.api.exams import router as exams_router
from app.api.flashcards import router as flashcards_router
from app.api.health import router as health_router
from app.api.homework import router as homework_router
from app.api.ingestion.routes import alias_router as ingestion_alias_router
from app.api.ingestion.routes import router as ingestion_router
from app.api.lessons import router as lessons_router
from app.api.topics import router as topics_router
from app.api.elements import router as elements_router
from app.api.study_plans import router as study_plans_router
from app.api.progress import router as progress_router
from app.api.quizzes import router as quizzes_router
from app.api.rag.routes import router as rag_router
from app.api.student_profile import router as student_profile_router
from app.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(student_profile_router)
api_router.include_router(chapters_router)
api_router.include_router(lessons_router)
api_router.include_router(topics_router)
api_router.include_router(elements_router)
api_router.include_router(study_plans_router)
api_router.include_router(chat_router)
api_router.include_router(rag_router)
api_router.include_router(ingestion_router)
api_router.include_router(ingestion_alias_router)
api_router.include_router(quizzes_router)
api_router.include_router(exams_router)
api_router.include_router(homework_router)
api_router.include_router(progress_router)
api_router.include_router(flashcards_router)
api_router.include_router(health_router)
