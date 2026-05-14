from __future__ import annotations
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env",
        ),
        case_sensitive=False,
        extra="ignore",
    )

    # GLM / Zhipu AI
    glm_api_key: str = ""
    glm_model: str = "glm-4v-plus"          # vision model for OCR
    glm_ocr_timeout: int = 60               # seconds per page

    # Internal auth (same key as other services)
    internal_api_key: str = "internal-dev-key"

    # Service URLs (for AIS cross-reference calls)
    finance_service_url: str = "http://finance-service:8000"

    # Document processing limits
    max_pdf_pages: int = 20
    max_upload_size_mb: int = 10

    environment: str = "development"


settings = Settings()
