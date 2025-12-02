import os
import re

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, computed_field
from functools import lru_cache
from pathlib import Path
from typing import Literal

# Load .env from project root (parent directory of webapp/)
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Loads configuration from the shared .env file at the project root.
    Uses Pydantic v2 for validation and type safety.
    """

    # Database
    DATABASE_URL: str
    """PostgreSQL database URL. Will be converted to async format for asyncpg."""

    # Redis
    REDIS_URL: str | None = None
    """Redis connection URL for caching (optional, e.g., redis://localhost:6379)"""

    # Supabase
    VITE_SUPABASE_URL: str
    """Supabase project URL (e.g., https://your-project.supabase.co)"""

    VITE_SUPABASE_ANON_KEY: str
    """Supabase anonymous/public API key"""

    SUPABASE_SERVICE_ROLE_KEY: str
    """Supabase service role key for admin operations"""

    # AWS SES
    AWS_REGION: str
    """AWS region for SES (e.g., us-east-1)"""

    AWS_ACCESS_KEY_ID: str
    """AWS access key ID for SES"""

    AWS_SECRET_ACCESS_KEY: str
    """AWS secret access key for SES"""

    AWS_SES_FROM_EMAIL: str
    """Email address to send notifications from"""

    # Application
    PYTHON_ENV: Literal["development", "production", "test"] = "development"
    """Environment mode: development, production, or test"""

    VITE_API_BASE_URL: str = "http://localhost:5000"
    """Base URL for the API server"""

    FRONTEND_URL: str = "https://seatsteal.app"
    """Base URL for the frontend application"""

    # Scraper
    SCRAPER_CONCURRENT_LIMIT: int = 5
    """Maximum number of concurrent scraping tasks"""

    SCRAPER_RATE_LIMIT: int = 100
    """Maximum requests per minute for scrapers"""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    """Stripe secret API key"""

    STRIPE_WEBHOOK_SECRET: str = ""
    """Stripe webhook signing secret"""

    STRIPE_PLUS_PRICE_ID: str = ""
    """Stripe price ID for Plus tier subscription"""

    STRIPE_PRO_PRICE_ID: str = ""
    """Stripe price ID for Pro tier subscription"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        case_sensitive=True,
        extra="ignore",
    )

    @computed_field
    @property
    def async_database_url(self) -> str:
        """
        Convert PostgreSQL URL to async format for asyncpg.

        Converts: postgresql://... -> postgresql+asyncpg://...
        This is required for SQLAlchemy async engine with asyncpg driver.
        """
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            return self.DATABASE_URL
        else:
            # If it's already async or unknown format, return as-is
            return self.DATABASE_URL

    @field_validator("VITE_SUPABASE_URL")
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Validate Supabase URL format"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("VITE_SUPABASE_URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("VITE_API_BASE_URL", "FRONTEND_URL")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("AWS_SES_FROM_EMAIL")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email address format"""
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("AWS_SES_FROM_EMAIL must be a valid email address")
        return v.lower()

    @field_validator("SCRAPER_CONCURRENT_LIMIT", "SCRAPER_RATE_LIMIT")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate positive integers"""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.PYTHON_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.PYTHON_ENV == "development"

    @property
    def is_test(self) -> bool:
        """Check if running in test environment"""
        return self.PYTHON_ENV == "test"

    @property
    def effective_frontend_url(self) -> str:
        """
        Get the effective frontend URL, detecting Vercel preview deployments.

        In preview environments, constructs the corresponding frontend preview URL.
        Otherwise, returns the configured FRONTEND_URL.
        """
        vercel_env = os.environ.get("VERCEL_ENV")
        branch = os.environ.get("VERCEL_GIT_COMMIT_REF")

        if vercel_env == "preview" and branch:
            # Sanitize branch name to match Vercel's URL format
            sanitized_branch = re.sub(r"[^a-z0-9-]", "-", branch.lower())
            return f"https://seatsteal-frontend-git-{sanitized_branch}-seatsteal.vercel.app"

        return self.FRONTEND_URL


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings instance is created
    throughout the application lifecycle.
    """
    return Settings()


settings = get_settings()
