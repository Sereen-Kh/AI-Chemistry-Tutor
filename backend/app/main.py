import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.router import api_router
from app.core.config import PROJECT_DIR, settings
from app.core.middleware import RateLimitMiddleware
from app.database import init_sqlite_schema_for_dev
from app.schemas.common import HealthResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EduMind API...")
    init_sqlite_schema_for_dev()
    yield
    logger.info("Shutting down EduMind API...")

# PostgreSQL migrations are handled by Alembic. Local SQLite dev startup
# creates missing tables so Swagger/frontend smoke tests work from any cwd.
app = FastAPI(
    title="AI Chemistry Tutor API",
    description="Backend API for the AI Chemistry Tutor application",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "Authentication and onboarding"},
        {"name": "users", "description": "Current user profile"},
        {"name": "student-profile", "description": "Student personalization profile"},
        {"name": "chapters", "description": "Chemistry chapters"},
        {"name": "lessons", "description": "Chemistry lessons"},
        {"name": "chat", "description": "RAG-backed tutor chat"},
        {"name": "rag", "description": "Retrieval APIs"},
        {"name": "admin-ingestion", "description": "Admin ingestion and content QA"},
        {"name": "quizzes", "description": "Quiz and exam trainer"},
        {"name": "exams", "description": "Exam practice"},
        {"name": "homework", "description": "Homework text/photo solver"},
        {"name": "progress", "description": "Progress and achievements"},
        {"name": "flashcards", "description": "Flashcard review"},
        {"name": "health", "description": "Health checks"},
    ],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/media/books",
    StaticFiles(directory=str(PROJECT_DIR / "data" / "textbooks"), check_dir=False),
    name="book_media",
)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check():
    return HealthResponse(status="healthy", service="edumind-backend", version="1.0.0")
