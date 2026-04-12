from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "auth-service"
    environment: str = "development"

    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]
    hsts_enabled: bool = False  # Default to false in development

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

    db_url: str | None = None
    database_url: str | None = None

    jwt_secret: str

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_secure(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if v in ("secret", "changeme", "your-secret-key"):
            raise ValueError("Insecure JWT_SECRET")
        return v
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str | None = None

    @property
    def redis_connection_url(self) -> str:
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    auth_rate_limit_window_seconds: int = 300
    auth_rate_limit_login: int = 50
    auth_rate_limit_register: int = 20
    auth_lockout_attempts: int = 5
    auth_lockout_window_seconds: int = 900

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
