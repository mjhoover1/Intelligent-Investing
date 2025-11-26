"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings

# ===========================================
# Product Branding
# ===========================================
PRODUCT_NAME = "Signal Sentinel"
PRODUCT_TAGLINE = "Your AI-powered watchdog for market signals."
PRODUCT_VERSION = "1.0.0"
PRODUCT_DESCRIPTION = "Define the rules. Signal Sentinel watches the market."

# Brand Colors
BRAND_COLORS = {
    "sentinel_indigo": "#4F46E5",  # Primary - buttons, highlights, logo
    "deep_signal_blue": "#1E3A8A",  # Headers, navbars
    "signal_teal": "#14B8A6",       # Accent - indicator values, highlights
    "alert_red": "#DC2626",         # Negative alerts, drawdowns
    "bull_green": "#16A34A",        # Gains, positive indicators
    "soft_gray": "#E5E7EB",         # Borders, background elements
    "dark_slate": "#0F172A",        # Dark mode background
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./signal_sentinel.db"

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

    # Plaid Integration (for broker sync)
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"  # sandbox, development, production

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
