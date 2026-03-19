from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="/home/rohinvengatesh04/Smart-Spend-FYP/Smart-Spend-FYP/.env",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "parser-service"
    environment: str = "development"

    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    hsts_enabled: bool = False
    internal_api_key: str

    @field_validator("internal_api_key")
    @classmethod
    def internal_api_key_must_be_secure(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("INTERNAL_API_KEY must be at least 32 characters")
        return v

    # File Upload Security (Internal defense-in-depth)
    max_upload_size_mb: int = 15  # slightly larger to allow for service-to-service overhead if any
    allowed_extensions: list[str] = ["pdf", "jpg", "jpeg", "png", "csv", "xls", "xlsx"]
    allowed_mime_types: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    ai_service_url: str = "http://localhost:8004"

    # Local LLM (Ollama) settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_primary_model: str = "deepseek-r1:7b"
    ollama_fallback_model: str = "deepseek-r1:1.5b"
    llm_confidence_threshold: float = 0.85


settings = Settings()
