"""Configuration settings for the application."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


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
    
    # OpenAI Settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    
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
