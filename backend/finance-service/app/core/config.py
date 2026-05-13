from __future__ import annotations

import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "finance-service"
    environment: str = "development"

    # Override via ALLOWED_ORIGINS env var (JSON array) for production deployments
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
    hsts_enabled: bool = False

    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    @field_validator("db_password")
    @classmethod
    def db_password_must_be_set(cls, v: str) -> str:
        if not v or v in ("password", "changeme", "postgres"):
            raise ValueError("Insecure or missing DB_PASSWORD")
        return v

    database_url: str | None = None

    jwt_secret: str
    jwt_algorithm: str = "HS256"

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_secure(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str | None = None

    @property
    def redis_connection_url(self) -> str:
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    internal_api_key: str

    @field_validator("internal_api_key")
    @classmethod
    def internal_api_key_must_be_secure(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("INTERNAL_API_KEY must be at least 32 characters")
        return v

    encryption_key: str | None = None

    @field_validator("encryption_key")
    @classmethod
    def encryption_key_must_be_valid(cls, v: str | None) -> str | None:
        if v and len(v) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters")
        return v

    # Rate limiting
    finance_rate_limit_window_seconds: int = 60
    finance_rate_limit_default: int = 20
    finance_rate_limit_upload: int = 5
    # File Upload Security
    max_upload_size_mb: int = 10
    allowed_extensions: list[str] = ["pdf", "jpg", "jpeg", "png", "csv", "xls", "xlsx"]
    allowed_mime_types: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
