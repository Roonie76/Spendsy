from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    app_name: str = "ai-service"
    environment: str = "development"

    jwt_secret: str
    jwt_algorithm: str = "HS256"

    finance_service_url: str = "http://finance-service:8000"
    internal_api_key: str

    gemini_api_key: str | None = None
    google_api_key: str | None = None

    redis_url: str = "redis://redis:6379/0"


settings = Settings()
