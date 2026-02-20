"""Configuration settings for the application."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    app_name: str = "Contact Scraper API"
    debug: bool = False
    api_keys: str = ""  # Comma-separated list of valid API keys

    # Redis Settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""  # Optional Redis password
    cache_ttl: int = 86400  # Cache TTL in seconds (default: 24 hours)

    # OpenAI Settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_timeout: int = 20  # OpenAI API timeout in seconds
    request_timeout: int = 10  # HTTP request timeout for fetching pages

    # Supabase Settings
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "contact-scraper"

    # Worker Pool Settings
    max_workers: int = 2  # Maximum concurrent jobs
    csv_concurrent_workers: int = 10  # Concurrent requests within each CSV job

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_valid_api_keys(self) -> set[str]:
        """Parse and return set of valid API keys."""
        if not self.api_keys:
            return set()
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
