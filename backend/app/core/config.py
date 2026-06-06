from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "AI Chemistry Tutor"
    debug: bool = False
    database_url: str = "postgresql://edumind:edumind_pass@localhost:5432/edumind_db"
    async_database_url: str = ""
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 30
    gemini_api_key: str = ""
    google_api_key: str = ""
    model_name: str = "gemini-3.5-flash"
    ai_request_timeout_seconds: int = 12
    gemini_document_model: str = "gemini-3-flash-preview"
    gemini_document_fallback_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_provider: str = "auto"
    local_embedding_model: str = "intfloat/multilingual-e5-base"
    gemini_min_page_chars: int = 40
    gemini_min_completeness_score: float = 0.5
    pdf_direct_extraction_enabled: bool = True
    pdf_image_fallback_enabled: bool = True
    ocr_provider: str = "gemini"
    ocr_required_for_vision: bool = True
    allow_partial_ingestion: bool = False
    ingestion_mode: str = "production"
    admin_token: str = ""
    admin_emails: List[str] = []
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    @property
    def effective_gemini_api_key(self) -> str:
        return self.gemini_api_key or self.google_api_key

    @property
    def effective_async_database_url(self) -> str:
        if self.async_database_url:
            return self.async_database_url
        if self.database_url.startswith("sqlite:///"):
            return self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        return self.database_url

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "off", "false", "0"}:
                return False
            if normalized in {"dev", "development", "on", "true", "1"}:
                return True
        return value

    @field_validator("ingestion_mode", mode="before")
    @classmethod
    def validate_ingestion_mode(cls, value):
        normalized = str(value or "production").strip().lower()
        if normalized not in {"dry_run", "production"}:
            raise ValueError("INGESTION_MODE must be either 'dry_run' or 'production'")
        return normalized

    @field_validator("embedding_provider", mode="before")
    @classmethod
    def validate_embedding_provider(cls, value):
        normalized = str(value or "auto").strip().lower()
        allowed = {"auto", "gemini", "local_multilingual", "local_hash"}
        if normalized not in allowed:
            raise ValueError(f"EMBEDDING_PROVIDER must be one of: {', '.join(sorted(allowed))}")
        return normalized

    class Config:
        env_file = (PROJECT_DIR / ".env", BACKEND_DIR / ".env")
        extra = "ignore"


settings = Settings()
