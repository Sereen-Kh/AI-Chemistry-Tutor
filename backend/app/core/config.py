from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    RESEND_API_KEY: str
    EMAIL_FROM: str
    NGROK_AUTH_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file = ".env"
    )

settings = Settings()