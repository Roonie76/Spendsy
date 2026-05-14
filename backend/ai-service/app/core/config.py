from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra="ignore"
    )

    app_name: str = "ai-service"
    environment: str = "development"

    jwt_secret: str
    jwt_algorithm: str = "HS256"

    finance_service_url: str = "http://finance-service:8000"
    internal_api_key: str

    gemini_api_key: str | None = None
    google_api_key: str | None = None

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str | None = None

    @property
    def redis_connection_url(self) -> str:
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/0"
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "https://spendsy-fintech.vercel.app",
    ]


settings = Settings()
