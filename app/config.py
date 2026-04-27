from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Competitive Intelligence Scraper"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 20

    # Cache TTL (seconds)
    CACHE_TTL_PRICING: int = 3600
    CACHE_TTL_PRODUCT: int = 7200
    CACHE_TTL_SEARCH: int = 1800

    # Scraper
    MAX_CONCURRENT_SCRAPERS: int = 10
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0

    # Rate limiting (per domain)
    RATE_LIMIT_REQUESTS: int = 5
    RATE_LIMIT_WINDOW: int = 10

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
