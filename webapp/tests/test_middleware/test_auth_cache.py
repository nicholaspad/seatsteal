"""Tests for authentication middleware caching functionality."""

import pytest
from unittest.mock import MagicMock, patch, call
from uuid import uuid4
from sqlalchemy.orm import Session

from api.middleware.auth import get_current_user
from models.user import Profile


class TestAuthenticationCaching:
    """Tests for user profile caching in authentication."""

    @pytest.mark.unit
    async def test_cache_miss_queries_database_and_caches_result(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that cache miss queries database and caches the result."""
        with patch("api.middleware.auth.supabase") as mock_supabase, patch(
            "api.middleware.auth.get_cached_user_profile"
        ) as mock_get_cache, patch(
            "api.middleware.auth.cache_user_profile"
        ) as mock_cache_profile:

            # Setup: Cache miss
            mock_get_cache.return_value = None

            # Mock Supabase returning valid user
            mock_user = MagicMock()
            mock_user.id = str(test_user.id)
            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            # Execute
            result = await get_current_user(mock_credentials, test_db)

            # Verify: Database was queried
            assert result.id == test_user.id
            assert result.email == test_user.email

            # Verify: Result was cached with 300s TTL
            mock_cache_profile.assert_called_once()
            call_args = mock_cache_profile.call_args
            assert call_args[0][0] == str(test_user.id)  # user_id
            assert call_args[1]["ttl"] == 300  # TTL

            # Verify cached data structure
            cached_data = call_args[0][1]
            assert cached_data["id"] == str(test_user.id)
            assert cached_data["email"] == test_user.email
            assert cached_data["role"] == test_user.role
            assert cached_data["college_id"] == test_user.college_id

    @pytest.mark.unit
    async def test_cache_hit_skips_database_query(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that cache hit returns cached data without querying database."""
        with patch("api.middleware.auth.supabase") as mock_supabase, patch(
            "api.middleware.auth.get_cached_user_profile"
        ) as mock_get_cache, patch(
            "api.middleware.auth.cache_user_profile"
        ) as mock_cache_profile:

            # Setup: Cache hit with profile data
            cached_profile = {
                "id": str(test_user.id),
                "email": test_user.email,
                "phone": test_user.phone,
                "role": test_user.role,
                "college_id": test_user.college_id,
            }
            mock_get_cache.return_value = cached_profile

            # Mock Supabase (this would normally happen before cache check)
            mock_user = MagicMock()
            mock_user.id = str(test_user.id)
            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            # Execute
            result = await get_current_user(mock_credentials, test_db)

            # Verify: Cache was checked
            mock_get_cache.assert_called_once_with(str(test_user.id))

            # Verify: Result matches cached data
            assert result.id == test_user.id
            assert result.email == test_user.email
            assert result.role == test_user.role
            assert result.college_id == test_user.college_id

            # Verify: Database was NOT queried (no new caching call)
            mock_cache_profile.assert_not_called()

            # Note: We can't easily verify no DB query without more complex mocking,
            # but the absence of cache_user_profile call indicates cache hit path

    @pytest.mark.unit
    async def test_cache_reconstructs_profile_object_correctly(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that cached data correctly reconstructs Profile object."""
        with patch("api.middleware.auth.supabase") as mock_supabase, patch(
            "api.middleware.auth.get_cached_user_profile"
        ) as mock_get_cache:

            # Setup: Cache hit with complete profile data
            cached_profile = {
                "id": str(test_user.id),
                "email": "cached@example.com",
                "phone": "+1234567890",
                "role": "admin",
                "college_id": 42,
            }
            mock_get_cache.return_value = cached_profile

            # Mock Supabase
            mock_user = MagicMock()
            mock_user.id = str(test_user.id)
            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            # Execute
            result = await get_current_user(mock_credentials, test_db)

            # Verify: Profile object has all cached attributes
            assert str(result.id) == cached_profile["id"]
            assert result.email == cached_profile["email"]
            assert result.phone == cached_profile["phone"]
            assert result.role == cached_profile["role"]
            assert result.college_id == cached_profile["college_id"]

    @pytest.mark.unit
    async def test_cache_handles_none_values_correctly(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that cache correctly handles None values (e.g., phone, college_id)."""
        with patch("api.middleware.auth.supabase") as mock_supabase, patch(
            "api.middleware.auth.get_cached_user_profile"
        ) as mock_get_cache:

            # Setup: Cache hit with None values
            cached_profile = {
                "id": str(test_user.id),
                "email": "test@example.com",
                "phone": None,
                "role": "user",
                "college_id": None,
            }
            mock_get_cache.return_value = cached_profile

            # Mock Supabase
            mock_user = MagicMock()
            mock_user.id = str(test_user.id)
            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            # Execute
            result = await get_current_user(mock_credentials, test_db)

            # Verify: Profile object correctly handles None values
            assert result.phone is None
            assert result.college_id is None

    @pytest.mark.unit
    async def test_cache_failure_falls_back_to_database(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that cache failures don't break authentication."""
        with patch("api.middleware.auth.supabase") as mock_supabase, patch(
            "api.middleware.auth.get_cached_user_profile"
        ) as mock_get_cache, patch(
            "api.middleware.auth.cache_user_profile"
        ) as mock_cache_profile:

            # Setup: Cache operations return None (simulating Redis failure)
            # Note: The real get_cached_user_profile catches exceptions and returns None
            mock_get_cache.return_value = None
            # cache_user_profile doesn't return anything, but we can verify it's called

            # Mock Supabase returning valid user
            mock_user = MagicMock()
            mock_user.id = str(test_user.id)
            mock_response = MagicMock()
            mock_response.user = mock_user
            mock_supabase.auth.get_user.return_value = mock_response

            mock_credentials = MagicMock()
            mock_credentials.credentials = "valid_token"

            # Execute: Should not raise exception despite cache miss
            result = await get_current_user(mock_credentials, test_db)

            # Verify: Authentication still succeeds using database
            assert result.id == test_user.id
            assert result.email == test_user.email

            # Cache operations were attempted
            mock_get_cache.assert_called_once_with(str(test_user.id))
            # Profile should be cached after database query
            mock_cache_profile.assert_called_once()
