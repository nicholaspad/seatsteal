"""Tests for authentication middleware."""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch
from uuid import uuid4

from api.middleware.auth import (
    get_current_user,
    get_optional_user,
    require_admin,
)
from models.user import Profile
from models.college import College


class TestGetCurrentUser:
    """Tests for get_current_user function."""

    @pytest.mark.unit
    async def test_invalid_token_format(
        self,
        test_db: Session,
    ):
        """Test with malformed JWT token."""
        with patch("api.middleware.auth.supabase") as mock_supabase:
            # Mock Supabase returning invalid response
            mock_supabase.auth.get_user.return_value = None

            # Create mock credentials
            mock_credentials = MagicMock()
            mock_credentials.credentials = "invalid_token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, test_db)

            assert exc_info.value.status_code == 401
            # Error messages are now sanitized to prevent information leakage
            assert "Authentication failed" in exc_info.value.detail

    @pytest.mark.unit
    async def test_expired_token(
        self,
        test_db: Session,
    ):
        """Test with expired JWT token."""
        with patch("api.middleware.auth.supabase") as mock_supabase:
            # Mock Supabase returning error for expired token
            mock_response = MagicMock()
            mock_response.user = None
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "expired_token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, test_db)

            assert exc_info.value.status_code == 401
            # Error messages are now sanitized to prevent information leakage
            assert "Authentication failed" in exc_info.value.detail

    @pytest.mark.unit
    async def test_valid_token_user_not_in_database(
        self,
        test_db: Session,
    ):
        """Test with valid JWT but user profile doesn't exist in database."""
        with patch("api.middleware.auth.supabase") as mock_supabase:
            # Mock Supabase returning valid user
            non_existent_user_id = str(uuid4())
            mock_user = MagicMock()
            mock_user.id = non_existent_user_id

            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, test_db)

            # Note: HTTPException with 404 gets caught by broad Exception handler
            # and re-raised as 401 with sanitized error message
            assert exc_info.value.status_code == 401
            assert "Authentication failed" in exc_info.value.detail

    @pytest.mark.unit
    async def test_invalid_user_id_format_not_uuid(
        self,
        test_db: Session,
    ):
        """Test with user ID that's not a valid UUID."""
        with patch("api.middleware.auth.supabase") as mock_supabase:
            # Mock Supabase returning invalid user ID format
            mock_user = MagicMock()
            mock_user.id = "not-a-valid-uuid"

            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, test_db)

            assert exc_info.value.status_code == 401
            assert "Invalid user ID format" in exc_info.value.detail

    @pytest.mark.unit
    async def test_supabase_connection_error(
        self,
        test_db: Session,
    ):
        """Test handling of Supabase connection errors."""
        with patch("api.middleware.auth.supabase") as mock_supabase:
            # Mock Supabase raising an exception
            mock_supabase.auth.get_user.side_effect = Exception("Connection timeout")

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, test_db)

            assert exc_info.value.status_code == 401
            # Error messages are now sanitized to prevent information leakage
            # The actual exception details ("Connection timeout") are logged
            # but not exposed to the client
            assert "Authentication failed" in exc_info.value.detail
            assert "Connection timeout" not in exc_info.value.detail


class TestGetOptionalUser:
    """Tests for get_optional_user function."""

    @pytest.mark.unit
    async def test_no_credentials_returns_none(
        self,
        test_db: Session,
    ):
        """Test that no credentials returns None instead of raising."""
        result = await get_optional_user(None, test_db)
        assert result is None

    @pytest.mark.unit
    async def test_invalid_token_returns_none(
        self,
        test_db: Session,
    ):
        """Test that invalid token returns None instead of raising."""
        with patch("api.middleware.auth.supabase") as mock_supabase:
            mock_supabase.auth.get_user.return_value = None

            mock_credentials = MagicMock()
            mock_credentials.credentials = "invalid_token"

            result = await get_optional_user(mock_credentials, test_db)
            assert result is None

    @pytest.mark.unit
    async def test_valid_token_returns_user(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that valid credentials return the user."""
        with patch("api.middleware.auth.supabase") as mock_supabase:
            # Mock Supabase returning valid user
            mock_user = MagicMock()
            mock_user.id = str(test_user.id)

            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            result = await get_optional_user(mock_credentials, test_db)
            assert result is not None
            assert result.id == test_user.id
            assert result.email == test_user.email


class TestRequireAdmin:
    """Tests for require_admin function."""

    @pytest.mark.unit
    def test_admin_user_success(
        self,
        test_admin_user: Profile,
    ):
        """Test that admin user passes through successfully."""
        result = require_admin(test_admin_user)
        assert result == test_admin_user
        assert result.role == "admin"

    @pytest.mark.unit
    def test_non_admin_user_raises_403(
        self,
        test_user: Profile,
    ):
        """Test that non-admin user raises 403 Forbidden."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin(test_user)

        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.detail
