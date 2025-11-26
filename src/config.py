"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./intelligent_investing.db"

    # OpenAI
    openai_api_key: str = ""

    # Telegram notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Market Data
    price_cache_seconds: int = 60

    # Monitoring
    monitor_interval_seconds: int = 300

    # Logging
    log_level: str = "INFO"

    # Default user (for MVP single-user mode)
    default_user_email: str = "user@localhost"

    # API Security
    api_key: str = ""  # Set in .env for production

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
