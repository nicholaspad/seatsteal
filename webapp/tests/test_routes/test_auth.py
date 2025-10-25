"""Tests for authentication API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from webapp.models.college import College
from webapp.models.user import Profile
from webapp.models.early_access_email import EarlyAccessEmail


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
        # Mock Supabase sign_in_with_otp
        mock_auth_response = MagicMock()
        mock_auth_response.error = None
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
        # Mock Supabase error
        mock_auth_response = MagicMock()
        mock_auth_response.error = "Supabase error"
        mock_supabase.auth.sign_in_with_otp.return_value = mock_auth_response

        response = await client.post(
            "/api/auth/admin-signin",
            json={"email": test_admin_user.email},
        )

        assert response.status_code == 500
        assert "Failed to send magic link" in response.json()["detail"]


class TestCheckEarlyAccess:
    """Tests for POST /api/auth/check-early-access endpoint."""

    @pytest.mark.unit
    async def test_check_early_access_has_access(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test checking early access for user with access."""
        email = "earlyuser@example.edu"

        # Create early access entry
        early_access = EarlyAccessEmail(
            email=email,
            is_active=True,
        )
        test_db.add(early_access)
        test_db.commit()

        response = await client.post(
            "/api/auth/check-early-access",
            json={"email": email},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["hasEarlyAccess"] is True
        assert data["email"] == email

    @pytest.mark.unit
    async def test_check_early_access_no_access(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test checking early access for user without access."""
        email = "nouser@example.edu"

        response = await client.post(
            "/api/auth/check-early-access",
            json={"email": email},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["hasEarlyAccess"] is False
        assert data["email"] == email

    @pytest.mark.unit
    async def test_check_early_access_inactive(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test checking early access for inactive entry."""
        email = "inactive@example.edu"

        # Create inactive early access entry
        early_access = EarlyAccessEmail(
            email=email,
            is_active=False,
        )
        test_db.add(early_access)
        test_db.commit()

        response = await client.post(
            "/api/auth/check-early-access",
            json={"email": email},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["hasEarlyAccess"] is False

    @pytest.mark.unit
    async def test_check_early_access_invalid_email(
        self,
        client: AsyncClient,
    ):
        """Test checking early access with non-.edu email."""
        response = await client.post(
            "/api/auth/check-early-access",
            json={"email": "notanedu@gmail.com"},
        )

        assert response.status_code == 400
        assert ".edu" in response.json()["detail"]

    @pytest.mark.unit
    async def test_check_early_access_invalid_email_format(
        self,
        client: AsyncClient,
    ):
        """Test checking early access with invalid email format."""
        response = await client.post(
            "/api/auth/check-early-access",
            json={"email": "notanemail"},
        )

        assert response.status_code == 422  # Pydantic validation error
