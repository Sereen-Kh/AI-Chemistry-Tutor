from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "AI Chemistry Tutor"
    debug: bool = False
    database_url: str = "sqlite:///./chemistry_tutor.db"
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 30
    gemini_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""
    model_name: str = "gemini-2.5-flash"
    embedding_model: str = "models/text-embedding-004"
    ocr_provider: str = "gemini"
    ocrarena_cookie: str = ""
    ocrarena_public_base_url: str = ""
    ocrarena_model_id: str = ""
    admin_token: str = ""
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    @property
    def effective_gemini_api_key(self) -> str:
        return self.gemini_api_key or self.google_api_key

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

    class Config:
        env_file = (PROJECT_DIR / ".env", BACKEND_DIR / ".env")
        extra = "ignore"


settings = Settings()
