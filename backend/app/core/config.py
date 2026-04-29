from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    app_name: str = "AI Chemistry Tutor"
    debug: bool = False
    database_url: str = "sqlite:///./chemistry_tutor.db"
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 30
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
