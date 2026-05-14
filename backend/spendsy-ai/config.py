import json
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILES = (
    os.path.join(BASE_DIR, ".env"),
    os.path.join(os.path.dirname(BASE_DIR), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), ".env"),
)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        case_sensitive=False, 
        extra="ignore"
    )

    finance_service_url: str = "http://localhost:8002"
    internal_api_key: str = "internal-dev-key"
    google_api_key: str | None = None
    e2b_api_key: str | None = None
    obscura_cdp_url: str = "ws://obscura:9222"
    allowed_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:3000,"
        "http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:5174,"
        "http://127.0.0.1:3000,http://127.0.0.1:8080,"
        "https://spendsy-fintech.vercel.app"
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        value = self.allowed_origins.strip()
        if value.startswith("["):
            parsed = json.loads(value)
            return [origin.strip() for origin in parsed if origin.strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    
    # Ollama Configuration (Local Inference)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_keep_alive: int = 300  # Default to 5m to avoid constant reloading
    model_gemma: str = "gemma4:e2b"
    model_llama: str = "gemma4:e2b"
    # TORA+ models — will be configured after fine-tuning
    model_tora_plus: str = ""             # Disabled until fine-tuning is complete
    
    # Conversation Memory Configuration
    redis_url: str | None = None  # Optional: "redis://localhost:6379/0" for high-scale deployments
    memory_backend: str = "database"  # "database" or "redis"
    use_persistent_memory: bool = True  # Enable conversation persistence

    # Obsidian Vault Configuration
    vault_base_path: str = "/data/vaults"  # Per-user vaults: /data/vaults/user_{id}/

settings = Settings()
