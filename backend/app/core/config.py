from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    RESEND_API_KEY: str
    EMAIL_FROM: str
    NGROK_AUTH_TOKEN: str = ""

    MODEL_API_URL: str
    MODEL_API_TOKEN: str

    CHEMISTRY_PDF_PATH: str
    CHROMA_DB_PATH: str
    
    GEMINI_API_KEY: str
    
    QUESTION_GEN_MODEL: str = "gemini-3.6-flash"
    QUESTION_REVIEW_MODEL: str = "gemini-3.6-flash"
    
    MIN_BANK_SIZE: int = 15
    
    HF_TOKEN: str | None = None

    anonymized_telemetry: bool = False
    model_config = SettingsConfigDict(
        env_file = ".env"
    )

settings = Settings()