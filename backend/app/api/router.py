"""API v1 router."""

from fastapi import APIRouter

from app.api.auth.routes import router as auth_router
from app.api.chat.routes import router as chat_router
from app.api.ingestion.routes import router as ingestion_router
from app.api.rag.routes import router as rag_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(rag_router)
api_router.include_router(ingestion_router)
