import json
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[2]
if (BACKEND_DIR.parent / "data").exists():
    PROJECT_DIR = BACKEND_DIR.parent
else:
    PROJECT_DIR = BACKEND_DIR


class Settings(BaseSettings):
    app_name: str = "AI Chemistry Tutor"
    debug: bool = False
    database_url: str = "postgresql://edumind:edumind_pass@localhost:5432/edumind_db"
    async_database_url: str = ""
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 30
    gemini_api_key: str = ""
    google_api_key: str = ""
    model_name: str = "gemini-2.5-flash"
    ai_request_timeout_seconds: int = 12
    gemini_tutor_generation_enabled: bool = True
    gemini_tutor_timeout_seconds: int = 12
    gemini_tutor_retry_attempts: int = 3
    gemini_failure_cooldown_seconds: int = 300
    gemini_semantic_helpers_enabled: bool = False
    gemini_semantic_helper_timeout_seconds: int = 10
    gemini_semantic_helper_retry_attempts: int = 3
    gemini_document_model: str = "gemini-2.5-flash"
    gemini_document_fallback_model: str = "gemini-2.5-pro,gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_reranker_model: str = "gemini-2.0-flash"
    embedding_provider: str = "gemini"
    embedding_dimension: int = 768
    allow_hash_embeddings: bool = False
    allow_local_embeddings: bool = False
    local_embedding_model: str = "intfloat/multilingual-e5-base"
    rag_query_logging_enabled: bool = True
    rag_student_retrieval_enabled: bool = True
    rag_active_reviewed_metadata_version: str = "2026-06-reviewed-v1"
    rag_require_production_gate: bool = False
    rag_evaluation_report_path: str = "data/eval/reports/rag_eval_latest.json"
    rag_qa_report_path: str = "backend/reports/rag_qa_report.json"
    audio_enabled: bool = False
    stt_provider: str = "elevenlabs"
    tts_provider: str = "elevenlabs"
    elevenlabs_api_key: str = ""
    elevenlabs_stt_model: str = "scribe_v2"
    elevenlabs_tts_model: str = "eleven_multilingual_v2"
    elevenlabs_default_voice_id: str = ""
    elevenlabs_base_url: str = "https://api.elevenlabs.io"
    audio_storage_dir: str = "data/uploads/audio"
    audio_public_base_url: str = "/media/uploads"
    audio_max_duration_seconds: int = 90
    audio_max_file_size_mb: int = 10
    allowed_audio_mime_types: List[str] = [
        "audio/webm",
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
    ]
    tts_max_chars_per_response: int = 1200
    firebase_project_id: str = ""
    firebase_service_account_json: str = ""
    firebase_web_vapid_public_key: str = ""
    expo_push_enabled: bool = True
    notification_push_timeout_seconds: int = 10
    gemini_min_page_chars: int = 40
    gemini_min_completeness_score: float = 0.5
    pdf_direct_extraction_enabled: bool = True
    pdf_image_fallback_enabled: bool = True
    ocr_provider: str = "gemini"
    ocr_required_for_vision: bool = True
    allow_partial_ingestion: bool = False
    allow_partial_solution_book_ingestion: bool = False
    ingestion_mode: str = "production"
    admin_token: str = ""
    admin_emails: List[str] = []
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    rate_limit_enabled: bool = True
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

    @staticmethod
    def _resolve_sqlite_url(url: str) -> str:
        parsed = make_url(url)
        if not parsed.get_backend_name().startswith("sqlite"):
            return url
        database = parsed.database
        if not database or database == ":memory:" or Path(database).is_absolute():
            return url
        return str(parsed.set(database=str((BACKEND_DIR / database).resolve())))

    @property
    def resolved_database_url(self) -> str:
        return self._resolve_sqlite_url(self.database_url)

    @property
    def resolved_effective_async_database_url(self) -> str:
        return self._resolve_sqlite_url(self.effective_async_database_url)

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
        normalized = str(value or "gemini").strip().lower()
        allowed = {"auto", "gemini", "local_multilingual", "local_hash"}
        if normalized not in allowed:
            raise ValueError(f"EMBEDDING_PROVIDER must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("embedding_dimension", mode="before")
    @classmethod
    def validate_embedding_dimension(cls, value):
        dimension = int(value or 768)
        if dimension != 768:
            raise ValueError("EMBEDDING_DIMENSION must be 768 unless the pgvector column is migrated")
        return dimension

    @field_validator("rag_active_reviewed_metadata_version", mode="before")
    @classmethod
    def validate_active_reviewed_metadata_version(cls, value):
        return str(value or "").strip()

    @field_validator("allowed_audio_mime_types", mode="before")
    @classmethod
    def parse_allowed_audio_mime_types(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    class Config:
        env_file = (PROJECT_DIR / ".env", BACKEND_DIR / ".env")
        extra = "ignore"


settings = Settings()
