"""Tests for authentication API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from models.college import College
from models.user import Profile


class TestUpdateCollege:
    """Tests for PATCH /api/auth/update-college endpoint."""

    @pytest.mark.unit
    async def test_update_college_success(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college: College,
    ):
        """Test successfully updating user's college."""
        # Create a second college
        new_college = College(
            name="New University",
            short_name="NU",
            is_active=True,
        )
        test_db.add(new_college)
        test_db.commit()
        test_db.refresh(new_college)

        response = await authenticated_client.patch(
            "/api/auth/update-college",
            json={"collegeId": new_college.id},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json
        assert data["user"]["collegeId"] == new_college.id

    @pytest.mark.unit
    async def test_update_college_not_found(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test updating to non-existent college."""
        response = await authenticated_client.patch(
            "/api/auth/update-college",
            json={"collegeId": 99999},
        )

        assert response.status_code == 404
        assert "College not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_update_college_inactive(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test updating to inactive college."""
        inactive_college = College(
            name="Inactive University",
            short_name="IU",
            is_active=False,
        )
        test_db.add(inactive_college)
        test_db.commit()
        test_db.refresh(inactive_college)

        response = await authenticated_client.patch(
            "/api/auth/update-college",
            json={"collegeId": inactive_college.id},
        )

        assert response.status_code == 400
        assert "not active" in response.json()["detail"]

    @pytest.mark.unit
    async def test_update_college_unauthenticated(self, client: AsyncClient):
        """Test updating college without authentication."""
        response = await client.patch(
            "/api/auth/update-college",
            json={"collegeId": 1},
        )

        assert response.status_code == 401


class TestAdminSignIn:
    """Tests for POST /api/auth/admin-signin endpoint."""

    @pytest.mark.unit
    async def test_admin_signin_success(
        self,
        client: AsyncClient,
        test_db: Session,
        test_admin_user: Profile,
        mock_supabase,
    ):
        """Test successful admin sign-in."""
        # Mock Supabase sign_in_with_otp to return successfully
        mock_auth_response = MagicMock()
        mock_supabase.auth.sign_in_with_otp.return_value = mock_auth_response

        response = await client.post(
            "/api/auth/admin-signin",
            json={"email": test_admin_user.email},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        assert "magic link sent" in response_json["message"].lower()

    @pytest.mark.unit
    async def test_admin_signin_user_not_found(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test admin sign-in with non-existent user."""
        response = await client.post(
            "/api/auth/admin-signin",
            json={"email": "nonexistent@example.edu"},
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_admin_signin_non_admin_user(
        self,
        client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test admin sign-in with non-admin user."""
        response = await client.post(
            "/api/auth/admin-signin",
            json={"email": test_user.email},
        )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    @pytest.mark.unit
    async def test_admin_signin_supabase_error(
        self,
        client: AsyncClient,
        test_db: Session,
        test_admin_user: Profile,
        mock_supabase,
    ):
        """Test admin sign-in with Supabase error."""
        # Mock Supabase to raise an exception (Python SDK behavior)
        mock_supabase.auth.sign_in_with_otp.side_effect = Exception("Supabase error")

        response = await client.post(
            "/api/auth/admin-signin",
            json={"email": test_admin_user.email},
        )

        assert response.status_code == 500
        # Security: Error messages are now sanitized to prevent information leakage
        # The actual error details ("Supabase error") are logged but not exposed
        assert "Failed to send admin sign-in email" in response.json()["detail"]
