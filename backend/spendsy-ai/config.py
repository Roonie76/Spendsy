import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        case_sensitive=False, 
        extra="ignore"
    )

    finance_service_url: str = "http://localhost:8002"
    internal_api_key: str = "internal-dev-key"
    google_api_key: str | None = None
    mistral_api_key: str | None = None
    
    # Ollama Configuration (Local Inference)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_keep_alive: int = 0  # 0 unloads model immediately for memory safety (24GB RAM constraint)
    model_gemma: str = "gemma4:e4b"       # Primary (TORA) — Gemma 4 E4B (reliable numeric reasoning)
    model_llama: str = "gemma4:e2b"       # Lightweight fallback — Gemma 4 E2B
    # TORA+ models — will be configured after fine-tuning
    model_tora_plus: str = ""             # Disabled until fine-tuning is complete
    
    # Conversation Memory Configuration
    redis_url: str | None = None  # Optional: "redis://localhost:6379/0" for high-scale deployments
    memory_backend: str = "database"  # "database" or "redis"
    use_persistent_memory: bool = True  # Enable conversation persistence

settings = Settings()
