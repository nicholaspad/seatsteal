from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Load .env from project root (parent directory of webapp/)
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # AWS SES
    AWS_REGION: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_SES_FROM_EMAIL: str

    # Application
    PYTHON_ENV: str = "development"
    API_BASE_URL: str = "http://localhost:5000"
    FRONTEND_URL: str = "http://localhost:5173"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Scraper
    SCRAPER_CONCURRENT_LIMIT: int = 5
    SCRAPER_RATE_LIMIT: int = 100

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()