"""
Comprehensive test suite for config.py

Tests application settings and configuration management including:
- Settings loading from environment variables
- Field validation (URLs, email, etc.)
- Computed fields
- Environment mode properties
- Service enablement checks
- Settings singleton caching
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from config import Settings, get_settings


@pytest.fixture
def minimal_env():
    """Minimum required environment variables for Settings"""
    return {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",
        "VITE_SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test_service_key",
    }


@pytest.fixture
def full_env(minimal_env):
    """Complete environment variables"""
    return {
        **minimal_env,
        "REDIS_URL": "redis://localhost:6379",
        "VITE_SUPABASE_ANON_KEY": "test_anon_key",
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
        "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "AWS_SES_FROM_EMAIL": "notifications@seatsteal.app",
        "PYTHON_ENV": "production",
        "VITE_API_BASE_URL": "https://api.seatsteal.app",
        "FRONTEND_URL": "https://seatsteal.app",
        "STRIPE_SECRET_KEY": "sk_test_123456789",
        "STRIPE_WEBHOOK_SECRET": "whsec_test_123456789",
        "STRIPE_PLUS_PRICE_ID": "price_plus_monthly",
        "STRIPE_PRO_PRICE_ID": "price_pro_monthly",
        "STRIPE_PLUS_ANNUAL_PRICE_ID": "price_plus_annual",
        "STRIPE_PRO_ANNUAL_PRICE_ID": "price_pro_annual",
        "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "TWILIO_AUTH_TOKEN": "test_auth_token",
        "TWILIO_FROM_NUMBER": "+15551234567",
        "TRUSTED_PROXIES": '["192.168.1.1", "10.0.0.1"]',
    }


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear get_settings cache before each test"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ============================================================================
# Settings Loading Tests
# ============================================================================


class TestSettingsLoading:
    """Test settings loading from environment variables"""

    def test_settings_load_from_environment(self, minimal_env):
        """Test loading settings from environment variables"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.DATABASE_URL == minimal_env["DATABASE_URL"]
            assert settings.VITE_SUPABASE_URL == minimal_env["VITE_SUPABASE_URL"]
            assert (
                settings.SUPABASE_SERVICE_ROLE_KEY
                == minimal_env["SUPABASE_SERVICE_ROLE_KEY"]
            )

    def test_settings_defaults(self, minimal_env):
        """Test default values for optional fields"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings(_env_file=None)

            # Optional fields with defaults
            assert settings.REDIS_URL is None
            assert settings.VITE_SUPABASE_ANON_KEY is None
            assert settings.AWS_REGION == ""
            assert settings.AWS_ACCESS_KEY_ID == ""
            assert settings.AWS_SECRET_ACCESS_KEY == ""
            assert settings.AWS_SES_FROM_EMAIL == "notifications@seatsteal.app"
            assert settings.PYTHON_ENV == "development"
            assert settings.VITE_API_BASE_URL == "http://localhost:5000"
            assert settings.FRONTEND_URL == "https://seatsteal.app"
            assert settings.STRIPE_SECRET_KEY == ""
            assert settings.STRIPE_WEBHOOK_SECRET == ""
            assert settings.TWILIO_ACCOUNT_SID == ""
            assert settings.TWILIO_AUTH_TOKEN == ""
            assert settings.TWILIO_FROM_NUMBER == ""
            assert settings.TRUSTED_PROXIES == []

    def test_settings_required_fields_missing(self):
        """Test that missing required fields raise ValidationError"""
        # Missing DATABASE_URL
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            errors = exc_info.value.errors()
            error_fields = [e["loc"][0] for e in errors]
            assert "DATABASE_URL" in error_fields

    def test_settings_required_fields_all_present(self, minimal_env):
        """Test successful creation with all required fields"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings(_env_file=None)

            assert settings is not None
            assert settings.DATABASE_URL is not None
            assert settings.VITE_SUPABASE_URL is not None
            assert settings.SUPABASE_SERVICE_ROLE_KEY is not None

    def test_settings_full_configuration(self, full_env):
        """Test loading complete configuration"""
        with patch.dict(os.environ, full_env, clear=True):
            settings = Settings(_env_file=None)

            # Verify all fields loaded
            assert settings.DATABASE_URL == full_env["DATABASE_URL"]
            assert settings.REDIS_URL == full_env["REDIS_URL"]
            assert settings.AWS_REGION == full_env["AWS_REGION"]
            assert settings.PYTHON_ENV == "production"
            assert settings.STRIPE_SECRET_KEY == full_env["STRIPE_SECRET_KEY"]
            assert settings.TWILIO_ACCOUNT_SID == full_env["TWILIO_ACCOUNT_SID"]


# ============================================================================
# Database URL Validation and Conversion Tests
# ============================================================================


class TestDatabaseURL:
    """Test DATABASE_URL field and async_database_url computed field"""

    def test_database_url_postgres_format(self, minimal_env):
        """Test accepting valid PostgreSQL URLs"""
        test_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "postgresql://user@localhost/db",
            "postgresql://localhost/db",
        ]

        for url in test_urls:
            env = {**minimal_env, "DATABASE_URL": url}
            with patch.dict(os.environ, env, clear=True):
                settings = Settings(_env_file=None)
                assert settings.DATABASE_URL == url

    def test_async_database_url_conversion(self, minimal_env):
        """Test conversion of sync URL to async format"""
        env = {
            **minimal_env,
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert (
                settings.async_database_url
                == "postgresql+asyncpg://user:pass@localhost:5432/db"
            )

    def test_async_database_url_already_async(self, minimal_env):
        """Test that already async URLs are not double-converted"""
        env = {
            **minimal_env,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert (
                settings.async_database_url
                == "postgresql+asyncpg://user:pass@localhost:5432/db"
            )

    def test_async_database_url_psycopg2_format(self, minimal_env):
        """Test handling of postgresql+psycopg2:// URLs"""
        env = {
            **minimal_env,
            "DATABASE_URL": "postgresql+psycopg2://user:pass@localhost:5432/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            # Should return as-is (unknown format)
            assert (
                settings.async_database_url
                == "postgresql+psycopg2://user:pass@localhost:5432/db"
            )


# ============================================================================
# URL Validation Tests
# ============================================================================


class TestURLValidation:
    """Test URL field validation"""

    def test_supabase_url_valid_https(self, minimal_env):
        """Test valid HTTPS Supabase URL"""
        env = {**minimal_env, "VITE_SUPABASE_URL": "https://myproject.supabase.co"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.VITE_SUPABASE_URL == "https://myproject.supabase.co"

    def test_supabase_url_trailing_slash_removed(self, minimal_env):
        """Test that trailing slashes are removed"""
        env = {**minimal_env, "VITE_SUPABASE_URL": "https://myproject.supabase.co/"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.VITE_SUPABASE_URL == "https://myproject.supabase.co"

    def test_supabase_url_invalid_no_protocol(self, minimal_env):
        """Test that URLs without protocol are rejected"""
        env = {**minimal_env, "VITE_SUPABASE_URL": "myproject.supabase.co"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            errors = exc_info.value.errors()
            assert any("http://" in str(e) for e in errors)

    def test_api_base_url_valid(self, minimal_env):
        """Test valid API base URL"""
        env = {**minimal_env, "VITE_API_BASE_URL": "https://api.example.com"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.VITE_API_BASE_URL == "https://api.example.com"

    def test_frontend_url_valid(self, minimal_env):
        """Test valid frontend URL"""
        env = {**minimal_env, "FRONTEND_URL": "https://example.com"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.FRONTEND_URL == "https://example.com"

    def test_url_http_allowed(self, minimal_env):
        """Test that HTTP URLs are allowed (for development)"""
        env = {
            **minimal_env,
            "VITE_SUPABASE_URL": "http://localhost:54321",
            "VITE_API_BASE_URL": "http://localhost:5000",
            "FRONTEND_URL": "http://localhost:3000",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.VITE_SUPABASE_URL == "http://localhost:54321"
            assert settings.VITE_API_BASE_URL == "http://localhost:5000"
            assert settings.FRONTEND_URL == "http://localhost:3000"


# ============================================================================
# Email Validation Tests
# ============================================================================


class TestEmailValidation:
    """Test AWS_SES_FROM_EMAIL validation"""

    def test_email_valid(self, minimal_env):
        """Test valid email address"""
        env = {**minimal_env, "AWS_SES_FROM_EMAIL": "notifications@seatsteal.app"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.AWS_SES_FROM_EMAIL == "notifications@seatsteal.app"

    def test_email_lowercase_conversion(self, minimal_env):
        """Test email is converted to lowercase"""
        env = {**minimal_env, "AWS_SES_FROM_EMAIL": "Notifications@SeatSteal.App"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.AWS_SES_FROM_EMAIL == "notifications@seatsteal.app"

    def test_email_invalid_no_at_sign(self, minimal_env):
        """Test rejection of email without @ sign"""
        env = {**minimal_env, "AWS_SES_FROM_EMAIL": "notificationsseatsteal.app"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            errors = exc_info.value.errors()
            assert any("email" in str(e).lower() for e in errors)

    def test_email_invalid_no_domain(self, minimal_env):
        """Test rejection of email without proper domain"""
        env = {**minimal_env, "AWS_SES_FROM_EMAIL": "notifications@seatsteal"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            errors = exc_info.value.errors()
            assert any("email" in str(e).lower() for e in errors)


# ============================================================================
# Environment Mode Tests
# ============================================================================


class TestEnvironmentMode:
    """Test PYTHON_ENV field and related properties"""

    def test_environment_development_mode(self, minimal_env):
        """Test development environment mode"""
        env = {**minimal_env, "PYTHON_ENV": "development"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.PYTHON_ENV == "development"
            assert settings.is_development is True
            assert settings.is_production is False
            assert settings.is_test is False

    def test_environment_production_mode(self, minimal_env):
        """Test production environment mode"""
        env = {**minimal_env, "PYTHON_ENV": "production"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.PYTHON_ENV == "production"
            assert settings.is_production is True
            assert settings.is_development is False
            assert settings.is_test is False

    def test_environment_test_mode(self, minimal_env):
        """Test test environment mode"""
        env = {**minimal_env, "PYTHON_ENV": "test"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.PYTHON_ENV == "test"
            assert settings.is_test is True
            assert settings.is_development is False
            assert settings.is_production is False

    def test_environment_default_development(self, minimal_env):
        """Test default environment is development"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.PYTHON_ENV == "development"
            assert settings.is_development is True

    def test_environment_invalid_value(self, minimal_env):
        """Test rejection of invalid PYTHON_ENV values"""
        env = {**minimal_env, "PYTHON_ENV": "staging"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            errors = exc_info.value.errors()
            assert any("PYTHON_ENV" in str(e) for e in errors)


# ============================================================================
# Service Enablement Tests
# ============================================================================


class TestServiceEnablement:
    """Test service enablement property checks"""

    def test_twilio_enabled_with_all_credentials(self, minimal_env):
        """Test Twilio enabled when all credentials present"""
        env = {
            **minimal_env,
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "TWILIO_AUTH_TOKEN": "test_token",
            "TWILIO_FROM_NUMBER": "+15551234567",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.twilio_enabled is True

    def test_twilio_disabled_missing_sid(self, minimal_env):
        """Test Twilio disabled when SID missing"""
        env = {
            **minimal_env,
            "TWILIO_AUTH_TOKEN": "test_token",
            "TWILIO_FROM_NUMBER": "+15551234567",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.twilio_enabled is False

    def test_twilio_disabled_missing_auth_token(self, minimal_env):
        """Test Twilio disabled when auth token missing"""
        env = {
            **minimal_env,
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "TWILIO_FROM_NUMBER": "+15551234567",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.twilio_enabled is False

    def test_twilio_disabled_by_default(self, minimal_env):
        """Test Twilio disabled with default empty credentials"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.twilio_enabled is False

    def test_aws_ses_enabled_with_all_credentials(self, minimal_env):
        """Test AWS SES enabled when all credentials present"""
        env = {
            **minimal_env,
            "AWS_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.aws_ses_enabled is True

    def test_aws_ses_disabled_missing_region(self, minimal_env):
        """Test AWS SES disabled when region missing"""
        env = {
            **minimal_env,
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.aws_ses_enabled is False

    def test_aws_ses_disabled_by_default(self, minimal_env):
        """Test AWS SES disabled with default empty credentials"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.aws_ses_enabled is False


# ============================================================================
# Effective Frontend URL Tests
# ============================================================================


class TestEffectiveFrontendURL:
    """Test effective_frontend_url property with Vercel detection"""

    def test_effective_frontend_url_production(self, minimal_env):
        """Test returns configured URL in production"""
        env = {**minimal_env, "FRONTEND_URL": "https://seatsteal.app"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.effective_frontend_url == "https://seatsteal.app"

    def test_effective_frontend_url_vercel_preview(self, minimal_env):
        """Test constructs preview URL in Vercel preview environment"""
        env = {
            **minimal_env,
            "FRONTEND_URL": "https://seatsteal.app",
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": "feature/new-ui",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            expected = (
                "https://seatsteal-frontend-git-feature-new-ui-seatsteal.vercel.app"
            )
            assert settings.effective_frontend_url == expected

    def test_effective_frontend_url_vercel_preview_sanitization(self, minimal_env):
        """Test branch name sanitization in preview URLs"""
        env = {
            **minimal_env,
            "FRONTEND_URL": "https://seatsteal.app",
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": "Feature/New_UI-2024",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            # Should sanitize to lowercase with only alphanumeric and hyphens
            expected = "https://seatsteal-frontend-git-feature-new-ui-2024-seatsteal.vercel.app"
            assert settings.effective_frontend_url == expected

    def test_effective_frontend_url_vercel_production(self, minimal_env):
        """Test returns configured URL in Vercel production"""
        env = {
            **minimal_env,
            "FRONTEND_URL": "https://seatsteal.app",
            "VERCEL_ENV": "production",
            "VERCEL_GIT_COMMIT_REF": "main",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            # Should use configured URL, not construct preview URL
            assert settings.effective_frontend_url == "https://seatsteal.app"

    def test_effective_frontend_url_no_vercel(self, minimal_env):
        """Test returns configured URL when not in Vercel"""
        env = {**minimal_env, "FRONTEND_URL": "https://seatsteal.app"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.effective_frontend_url == "https://seatsteal.app"


# ============================================================================
# Stripe Configuration Tests
# ============================================================================


class TestStripeConfiguration:
    """Test Stripe-related settings"""

    def test_stripe_secret_key_loaded(self, minimal_env):
        """Test Stripe secret key is loaded"""
        env = {**minimal_env, "STRIPE_SECRET_KEY": "sk_test_123456789"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.STRIPE_SECRET_KEY == "sk_test_123456789"

    def test_stripe_webhook_secret_loaded(self, minimal_env):
        """Test Stripe webhook secret is loaded"""
        env = {**minimal_env, "STRIPE_WEBHOOK_SECRET": "whsec_test_123456789"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.STRIPE_WEBHOOK_SECRET == "whsec_test_123456789"

    def test_stripe_price_ids_loaded(self, minimal_env):
        """Test all Stripe price IDs are loaded"""
        env = {
            **minimal_env,
            "STRIPE_PLUS_PRICE_ID": "price_plus_monthly",
            "STRIPE_PRO_PRICE_ID": "price_pro_monthly",
            "STRIPE_PLUS_ANNUAL_PRICE_ID": "price_plus_annual",
            "STRIPE_PRO_ANNUAL_PRICE_ID": "price_pro_annual",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.STRIPE_PLUS_PRICE_ID == "price_plus_monthly"
            assert settings.STRIPE_PRO_PRICE_ID == "price_pro_monthly"
            assert settings.STRIPE_PLUS_ANNUAL_PRICE_ID == "price_plus_annual"
            assert settings.STRIPE_PRO_ANNUAL_PRICE_ID == "price_pro_annual"

    def test_stripe_optional_in_test_mode(self, minimal_env):
        """Test Stripe fields are optional (empty defaults)"""
        env = {**minimal_env, "PYTHON_ENV": "test"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.STRIPE_SECRET_KEY == ""
            assert settings.STRIPE_WEBHOOK_SECRET == ""


# ============================================================================
# Redis Configuration Tests
# ============================================================================


class TestRedisConfiguration:
    """Test Redis-related settings"""

    def test_redis_url_valid(self, minimal_env):
        """Test valid Redis URL"""
        env = {**minimal_env, "REDIS_URL": "redis://localhost:6379"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.REDIS_URL == "redis://localhost:6379"

    def test_redis_url_none_by_default(self, minimal_env):
        """Test Redis URL is None by default"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.REDIS_URL is None

    def test_redis_url_with_password(self, minimal_env):
        """Test Redis URL with authentication"""
        env = {**minimal_env, "REDIS_URL": "redis://:password@localhost:6379"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.REDIS_URL == "redis://:password@localhost:6379"


# ============================================================================
# Settings Singleton Tests
# ============================================================================


class TestSettingsSingleton:
    """Test get_settings() caching behavior"""

    def test_get_settings_returns_settings_instance(self, minimal_env):
        """Test get_settings returns Settings instance"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings = get_settings()

            assert isinstance(settings, Settings)

    def test_get_settings_singleton_behavior(self, minimal_env):
        """Test get_settings returns same instance"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2

    def test_get_settings_cache_efficiency(self, minimal_env):
        """Test get_settings doesn't reload from environment"""
        with patch.dict(os.environ, minimal_env, clear=True):
            settings1 = get_settings()

            # Change environment
            os.environ["DATABASE_URL"] = "postgresql://changed:5432/newdb"

            settings2 = get_settings()

            # Should still have original value (cached)
            assert settings2.DATABASE_URL == minimal_env["DATABASE_URL"]
            assert settings1 is settings2
