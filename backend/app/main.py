from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.auth.routes import router as auth_router
from app.database import engine, Base

# Create all tables on startup (SQLite for dev; swap DATABASE_URL for Postgres in prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Chemistry Tutor API",
    description="Backend API for the AI Chemistry Tutor application",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}

