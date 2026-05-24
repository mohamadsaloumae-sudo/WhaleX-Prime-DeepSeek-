"""WhaleX Prime - Configuration"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings"""
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://whalex:whalex_2026_secure@localhost:5432/whalex_prime"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    # Redis
    REDIS_URL: str = "redis://:whalex_redis_2026@localhost:6379"
    REDIS_PASSWORD: str = "whalex_redis_2026"

    # Security
    SECRET_KEY: str = "whalex_super_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Admin
    ADMIN_PASSWORD: str = "whalex2026admin"

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_CHAT_ID: Optional[str] = None

    # Binance
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None

    # Gas Fees
    GAS_FEE_PERCENT: float = 0.01
    MIN_GAS_BALANCE: float = 5.0

    # Referral
    REFERRAL_BASE_URL: str = "https://whalexapp.io/ref/"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    model_config = ConfigDict(env_file=".env", extra="ignore")


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings