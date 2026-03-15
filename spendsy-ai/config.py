from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    finance_service_url: str = "http://localhost:8002"
    internal_api_key: str = "internal-dev-key"
    tora_model: str = "deepseek-r1:1.5b"

settings = Settings()
