"""
Unit tests for error handling utilities.
"""

import pytest
from unittest.mock import patch
from fastapi import HTTPException

from utils.errors import log_and_raise_500, log_and_raise, sanitize_error_message


class TestLogAndRaise500:
    """Tests for log_and_raise_500 function."""

    @pytest.mark.unit
    def test_raises_500_with_generic_message(self):
        """Test that log_and_raise_500 raises HTTPException with status 500."""
        with pytest.raises(HTTPException) as exc_info:
            log_and_raise_500(
                "Failed to fetch data", Exception("Database connection failed")
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to fetch data"

    @pytest.mark.unit
    @patch("utils.errors.logger")
    def test_logs_full_exception_details(self, mock_logger):
        """Test that the full exception is logged for debugging."""
        original_error = Exception("Database connection failed")

        with pytest.raises(HTTPException):
            log_and_raise_500("Failed to fetch data", original_error)

        # Verify error was logged with exception info
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Failed to fetch data" in call_args[0][0]
        assert "Database connection failed" in call_args[0][0]
        assert call_args[1]["exc_info"] is True


class TestLogAndRaise:
    """Tests for log_and_raise function."""

    @pytest.mark.unit
    def test_raises_with_custom_status_code(self):
        """Test that log_and_raise raises HTTPException with custom status code."""
        with pytest.raises(HTTPException) as exc_info:
            log_and_raise(404, "Resource not found", Exception("No such record"))

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Resource not found"

    @pytest.mark.unit
    def test_raises_403_forbidden(self):
        """Test raising 403 Forbidden error."""
        with pytest.raises(HTTPException) as exc_info:
            log_and_raise(403, "Access denied", Exception("Insufficient permissions"))

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Access denied"

    @pytest.mark.unit
    @patch("utils.errors.logger")
    def test_logs_with_different_status_codes(self, mock_logger):
        """Test that exceptions are logged regardless of status code."""
        with pytest.raises(HTTPException):
            log_and_raise(400, "Bad request", Exception("Invalid input"))

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Bad request" in call_args[0][0]
        assert "Invalid input" in call_args[0][0]


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message function."""

    @pytest.mark.unit
    def test_returns_safe_message_unchanged(self):
        """Test that safe error messages are returned unchanged."""
        safe_message = "Invalid input format"
        result = sanitize_error_message(safe_message)
        assert result == safe_message

    @pytest.mark.unit
    def test_sanitizes_traceback(self):
        """Test that error messages with 'Traceback' are sanitized."""
        dangerous_msg = "Traceback (most recent call last):\n  File '/app/main.py'"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_file_paths(self):
        """Test that error messages with file paths are sanitized."""
        dangerous_msg = "Error in File /home/user/app/config.py at line 42"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_home_directory(self):
        """Test that error messages with /home/ paths are sanitized."""
        dangerous_msg = "Cannot read /home/admin/.env file"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_users_directory(self):
        """Test that error messages with /Users/ paths are sanitized."""
        dangerous_msg = "File not found: /Users/developer/secrets.json"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_password_in_error(self):
        """Test that error messages containing 'password=' are sanitized."""
        dangerous_msg = "Connection failed with password=secret123"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_secret_key(self):
        """Test that error messages containing 'secret=' are sanitized."""
        dangerous_msg = "API call failed with secret=abc123xyz"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_api_key(self):
        """Test that error messages containing 'key=' are sanitized."""
        dangerous_msg = "Authentication error: key=sk_live_123456"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_postgresql_connection_string(self):
        """Test that PostgreSQL connection strings are sanitized."""
        dangerous_msg = "Cannot connect to postgresql://user:pass@localhost/db"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_mysql_connection_string(self):
        """Test that MySQL connection strings are sanitized."""
        dangerous_msg = "Database error: mysql://root:password@localhost:3306/app"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_sqlite_connection_string(self):
        """Test that SQLite connection strings are sanitized."""
        dangerous_msg = "DB error: sqlite:///app.db with full path"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_redis_connection_string(self):
        """Test that Redis connection strings are sanitized."""
        dangerous_msg = "Cache error: redis://localhost:6379/0"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_aws_access_key(self):
        """Test that AWS access keys are sanitized."""
        dangerous_msg = "S3 error with aws_access_key: AKIAIOSFODNN7EXAMPLE"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_sanitizes_aws_secret(self):
        """Test that AWS secrets are sanitized."""
        dangerous_msg = "AWS error: aws_secret not valid"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        dangerous_msg = "Error with PASSWORD=secret"
        result = sanitize_error_message(dangerous_msg)
        assert result == "An internal error occurred"

    @pytest.mark.unit
    def test_multiple_patterns_trigger_sanitization(self):
        """Test that any sensitive pattern triggers sanitization."""
        test_cases = [
            "traceback information here",
            "file path leak",
            "/users/admin/config",
            "/home/root/.ssh/id_rsa",
            "password=leaked",
            "secret=exposed",
            "key=compromised",
            "postgresql://leak",
            "mysql://exposed",
            "sqlite://shown",
            "redis://revealed",
            "aws_access_key here",
            "aws_secret exposed",
        ]

        for msg in test_cases:
            result = sanitize_error_message(msg)
            assert (
                result == "An internal error occurred"
            ), f"Failed to sanitize: {msg}"

    @pytest.mark.unit
    def test_preserves_generic_error_messages(self):
        """Test that generic, safe error messages are preserved."""
        safe_messages = [
            "Invalid email format",
            "User not found",
            "Permission denied",
            "Rate limit exceeded",
            "Invalid JSON payload",
            "Missing required field: email",
            "Course code must be alphanumeric",
        ]

        for msg in safe_messages:
            result = sanitize_error_message(msg)
            assert result == msg, f"Incorrectly sanitized safe message: {msg}"
