from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    app_name: str = "auth-service"
    environment: str = "development"

    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str
    database_url: str | None = None

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    redis_url: str = "redis://redis:6379/0"
    auth_rate_limit_window_seconds: int = 300
    auth_rate_limit_login: int = 50
    auth_rate_limit_register: int = 20

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
