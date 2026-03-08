from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "finance-service"
    environment: str = "development"

    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str
    database_url: str | None = None

    jwt_secret: str
    jwt_algorithm: str = "HS256"

    parser_service_url: str = "http://parser-service:8000"

    redis_url: str = "redis://redis:6379/0"
    internal_api_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
