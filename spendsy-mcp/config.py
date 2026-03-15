from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    finance_service_url: str = "http://localhost:8002"
    parser_service_url: str = "http://localhost:8003"
    internal_api_key: str = "internal-dev-key"
    google_api_key: str | None = None
    spendsy_user_id: int = 1

settings = Settings()
