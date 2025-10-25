"""Tests for user API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import AsyncMock, patch

from webapp.models.user import Profile
from webapp.models.college import College


class TestGetUserSettings:
    """Tests for GET /api/user/settings endpoint."""

    @pytest.mark.unit
    async def test_get_user_settings_success(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
        test_college: College,
    ):
        """Test successfully getting user settings."""
        response = await authenticated_client.get("/api/user/settings")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["email"] == test_user.email
        assert data["phone"] == test_user.phone
        assert data["collegeId"] == test_college.id
        assert data["collegeName"] == test_college.name

    @pytest.mark.unit
    async def test_get_user_settings_no_college(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test getting user settings when user has no college."""
        # Update user to have no college
        test_user.college_id = None
        test_db.commit()

        response = await authenticated_client.get("/api/user/settings")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["collegeId"] == 0
        assert data["collegeName"] == ""

    @pytest.mark.unit
    async def test_get_user_settings_unauthenticated(self, client: AsyncClient):
        """Test getting user settings without authentication."""
        response = await client.get("/api/user/settings")

        assert response.status_code == 401


class TestUpdateUserSettings:
    """Tests for PUT /api/user/settings endpoint."""

    @pytest.mark.unit
    async def test_update_user_settings_phone(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test updating user phone number."""
        new_phone = "+9876543210"

        response = await authenticated_client.put(
            "/api/user/settings",
            json={"phone": new_phone},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["phone"] == new_phone
        assert response_json["collegeChanged"] is False

        # Verify in database
        test_db.refresh(test_user)
        assert test_user.phone == new_phone

    @pytest.mark.unit
    async def test_update_user_settings_college(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college: College,
    ):
        """Test updating user college."""
        # Create a new college
        new_college = College(
            name="New University",
            short_name="NU",
            is_active=True,
        )
        test_db.add(new_college)
        test_db.commit()
        test_db.refresh(new_college)

        response = await authenticated_client.put(
            "/api/user/settings",
            json={"collegeId": new_college.id},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["collegeId"] == new_college.id
        assert data["collegeName"] == new_college.name
        assert response_json["collegeChanged"] is True

    @pytest.mark.unit
    async def test_update_user_settings_both(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test updating both phone and college."""
        new_college = College(
            name="Another University",
            short_name="AU",
            is_active=True,
        )
        test_db.add(new_college)
        test_db.commit()
        test_db.refresh(new_college)

        new_phone = "+1111111111"

        response = await authenticated_client.put(
            "/api/user/settings",
            json={"phone": new_phone, "collegeId": new_college.id},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["phone"] == new_phone
        assert data["collegeId"] == new_college.id

    @pytest.mark.unit
    async def test_update_user_settings_invalid_college(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test updating with invalid college ID."""
        response = await authenticated_client.put(
            "/api/user/settings",
            json={"collegeId": 99999},
        )

        assert response.status_code == 404
        assert "College not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_update_user_settings_unauthenticated(self, client: AsyncClient):
        """Test updating settings without authentication."""
        response = await client.put(
            "/api/user/settings",
            json={"phone": "+1234567890"},
        )

        assert response.status_code == 401


class TestGetSubscriptionTier:
    """Tests for GET /api/user/subscription-tier endpoint."""

    @pytest.mark.unit
    async def test_get_subscription_tier_free(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test getting subscription tier for free user."""
        with patch(
            "webapp.api.routes.user.get_user_subscription_tier"
        ) as mock_get_tier:
            mock_get_tier.return_value = "free"

            response = await authenticated_client.get("/api/user/subscription-tier")

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["success"] is True
            data = response_json["data"]
            assert data["tier"] == "free"

    @pytest.mark.unit
    async def test_get_subscription_tier_plus(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test getting subscription tier for plus user."""
        with patch(
            "webapp.api.routes.user.get_user_subscription_tier"
        ) as mock_get_tier:
            mock_get_tier.return_value = "plus"

            response = await authenticated_client.get("/api/user/subscription-tier")

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["success"] is True
            data = response_json["data"]
            assert data["tier"] == "plus"

    @pytest.mark.unit
    async def test_get_subscription_tier_pro(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test getting subscription tier for pro user."""
        with patch(
            "webapp.api.routes.user.get_user_subscription_tier"
        ) as mock_get_tier:
            mock_get_tier.return_value = "pro"

            response = await authenticated_client.get("/api/user/subscription-tier")

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["success"] is True
            data = response_json["data"]
            assert data["tier"] == "pro"

    @pytest.mark.unit
    async def test_get_subscription_tier_unauthenticated(self, client: AsyncClient):
        """Test getting subscription tier without authentication."""
        response = await client.get("/api/user/subscription-tier")

        assert response.status_code == 401
