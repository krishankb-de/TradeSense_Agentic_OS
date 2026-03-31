"""Application configuration management."""

from functools import lru_cache
from typing import Literal
from pathlib import Path

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "tradesense"
    postgres_user: str = "tradesense"
    postgres_password: str = "changeme_secure_password"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "changeme_redis_password"

    # LLM Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    vllm_host: str = "http://localhost:8000"
    vllm_default_model: str = "deepseek-v3"
    llm_provider: Literal["ollama", "vllm"] = "ollama"
    use_gpu: bool = True
    cuda_visible_devices: str = "0"

    # Voice Processing
    whisper_model: str = "large-v3"
    whisper_device: Literal["cpu", "cuda"] = "cuda"
    whisper_compute_type: Literal["int8", "float16", "float32"] = "float16"
    piper_voice: str = "en_US-lessac-medium"
    piper_quality: Literal["low", "medium", "high"] = "high"
    vad_threshold: float = 0.5
    vad_min_speech_duration: int = 250
    voice_latency_target: int = 500

    # Azure OpenAI (Cloud-based LLM)
    azure_openai_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment_gpt4: str = "gpt-4"
    azure_openai_deployment_gpt35: str = "gpt-35-turbo"
    use_azure_openai: bool = False

    # Azure Speech Services (Cloud-based Voice)
    azure_speech_key: str = ""
    azure_speech_region: str = "eastus"
    azure_speech_language: str = "en-US"
    azure_speech_voice: str = "en-US-JennyNeural"
    use_azure_speech: bool = False

    # Google Gemini API (Free tier)
    google_api_key: str = ""
    use_gemini: bool = False

    # Open-Source Communication (No Twilio!)
    webrtc_signaling_url: str = "ws://localhost:8080"
    webrtc_stun_server: str = "stun:stun.l.google.com:19302"
    webrtc_turn_server: str = ""
    webrtc_turn_username: str = ""
    webrtc_turn_password: str = ""
    jitsi_domain: str = "meet.jit.si"
    jitsi_room_prefix: str = "tradesense-"
    jitsi_jwt_app_id: str = ""
    jitsi_jwt_secret: str = ""
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@tradesense.local"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "TradeSense <noreply@tradesense.local>"
    discord_webhook_url: str = ""
    freeswitch_host: str = "localhost"
    freeswitch_port: int = 8021
    freeswitch_password: str = "ClueCon"

    # InvenTree
    inventree_host: str = "http://localhost:8080"
    inventree_api_token: str = ""

    # Part-DB
    partdb_host: str = "http://localhost:8081"
    partdb_api_token: str = ""

    # KiCost
    kicost_distributors: str = "digikey,mouser,arrow,newark,tme"
    kicost_cache_ttl: int = 300

    # Carbon Tracking
    kabaun_emission_factors_path: str = "/data/emission-factors"
    kabaun_region: str = "US"
    codecarbon_enabled: bool = True
    codecarbon_tracking_mode: Literal["process", "machine"] = "process"

    # Observability
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    phoenix_host: str = "http://localhost:6006"
    phoenix_collector_endpoint: str = "http://localhost:6006/v1/traces"
    prometheus_host: str = "http://localhost:9090"
    
    # Datadog (Cloud-based observability)
    datadog_api_key: str = ""
    datadog_app_key: str = ""
    datadog_site: str = "datadoghq.com"
    datadog_service: str = "tradesense"
    datadog_env: str = "development"
    use_datadog: bool = False
    
    # Sentry (Error tracking)
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 1.0

    # ZenML
    zenml_store_type: Literal["local", "sql"] = "local"
    zenml_secrets_manager: Literal["local", "vault"] = "local"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = True

    # JWT
    jwt_secret_key: str = "changeme_jwt_secret_key_min_32_chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Security
    encryption_key: str = "changeme_encryption_key_32_bytes"

    # Feature Flags
    enable_voice_pipeline: bool = True
    enable_carbon_tracking: bool = True
    enable_multimodal: bool = True
    enable_local_llm: bool = False  # Disabled for cloud-based approach
    enable_local_voice: bool = False  # Disabled for cloud-based approach
    enable_ollama: bool = False
    enable_vllm: bool = False

    # Hardware Configuration
    deployment_profile: Literal["solo", "small", "medium", "enterprise"] = "small"
    max_concurrent_voice_sessions: int = 10
    max_concurrent_jobs: int = 100

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create a global settings instance for convenience
settings = get_settings()
