"""Tests for referral API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch
from uuid import uuid4

from models.user import Profile
from models.referral import Referral
from models.referral_redemption import ReferralRedemption
from models.college import College


@pytest.fixture
def second_user(test_db: Session, test_college: College) -> Profile:
    """Create a second test user (referee)."""
    user = Profile(
        id=str(uuid4()),
        email="referee@example.edu",
        phone="9876543210",
        college_id=test_college.id,
        role="user",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def third_user(test_db: Session, test_college: College) -> Profile:
    """Create a third test user (for testing multiple referral codes)."""
    user = Profile(
        id=str(uuid4()),
        email="thirduser@example.edu",
        phone="5555555555",
        college_id=test_college.id,
        role="user",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_referral(test_db: Session, test_user: Profile) -> Referral:
    """Create a test referral code."""
    referral = Referral(
        referrer_id=test_user.id,
        referral_code="TESTCODE",
    )
    test_db.add(referral)
    test_db.commit()
    test_db.refresh(referral)
    return referral


@pytest.fixture
def second_referral(test_db: Session, third_user: Profile) -> Referral:
    """Create a second referral code from third user."""
    referral = Referral(
        referrer_id=third_user.id,
        referral_code="TESTCODE2",
    )
    test_db.add(referral)
    test_db.commit()
    test_db.refresh(referral)
    return referral


class TestGetMyReferral:
    """Tests for GET /api/referrals/my-referral endpoint."""

    @pytest.mark.unit
    async def test_get_my_referral_creates_code(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that a referral code is created if none exists."""
        response = await authenticated_client.get("/api/referrals/my-referral")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert "referral_code" in data
        assert "referral_url" in data
        assert data["total_referrals"] == 0
        assert data["successful_referrals"] == 0

    @pytest.mark.unit
    async def test_get_my_referral_returns_existing(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_referral: Referral,
    ):
        """Test that existing referral code is returned."""
        response = await authenticated_client.get("/api/referrals/my-referral")

        assert response.status_code == 200
        response_json = response.json()
        data = response_json["data"]
        assert data["referral_code"] == "TESTCODE"

    @pytest.mark.unit
    async def test_get_my_referral_unauthenticated(self, client: AsyncClient):
        """Test that unauthenticated request fails."""
        response = await client.get("/api/referrals/my-referral")
        assert response.status_code == 401


class TestApplyReferralCode:
    """Tests for POST /api/referrals/apply endpoint."""

    @pytest.mark.unit
    async def test_apply_referral_code_success(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
        mock_supabase,
    ):
        """Test successfully applying a referral code."""
        # Create referral code for second_user (the referrer)
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="GOODCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        # Mock the trial creation functions
        with patch(
            "api.routes.referrals.create_referee_trial"
        ) as mock_referee_trial, patch(
            "api.routes.referrals.create_referrer_trial"
        ) as mock_referrer_trial:
            mock_referee_trial.return_value = "sub_referee_123"
            mock_referrer_trial.return_value = "sub_referrer_123"

            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "GOODCODE"},
            )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        assert "referral has been applied" in response_json["data"]["message"].lower()

        # Verify redemption was created
        redemption = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).first()
        )
        assert redemption is not None
        assert redemption.referral_id == referral.id

    @pytest.mark.unit
    async def test_apply_referral_code_invalid(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test applying an invalid referral code."""
        response = await authenticated_client.post(
            "/api/referrals/apply",
            json={"referral_code": "INVALID"},
        )

        assert response.status_code == 400
        assert "Invalid referral code" in response.json()["detail"]

    @pytest.mark.unit
    async def test_apply_own_referral_code(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
        test_referral: Referral,
    ):
        """Test that user cannot use their own referral code."""
        response = await authenticated_client.post(
            "/api/referrals/apply",
            json={"referral_code": "TESTCODE"},
        )

        assert response.status_code == 400
        assert "cannot use your own referral code" in response.json()["detail"].lower()

    @pytest.mark.unit
    async def test_apply_multiple_referral_codes_blocked(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
        third_user: Profile,
    ):
        """Test that user CANNOT claim multiple different referral codes.

        This is the CRITICAL security test that prevents trial abuse.
        Users should only be able to claim ONE referral code total.
        """
        # Create two different referral codes from different users
        referral1 = Referral(
            referrer_id=second_user.id,
            referral_code="CODE1",
        )
        referral2 = Referral(
            referrer_id=third_user.id,
            referral_code="CODE2",
        )
        test_db.add(referral1)
        test_db.add(referral2)
        test_db.commit()
        test_db.refresh(referral1)
        test_db.refresh(referral2)

        # Mock the trial creation functions
        with patch(
            "api.routes.referrals.create_referee_trial"
        ) as mock_referee_trial, patch(
            "api.routes.referrals.create_referrer_trial"
        ) as mock_referrer_trial:
            mock_referee_trial.return_value = "sub_referee_123"
            mock_referrer_trial.return_value = "sub_referrer_123"

            # First referral code should succeed
            response1 = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "CODE1"},
            )
            assert response1.status_code == 200

            # Second referral code from different user should FAIL
            response2 = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "CODE2"},
            )
            assert response2.status_code == 400
            assert (
                "already claimed a referral code" in response2.json()["detail"].lower()
            )

        # Verify only one redemption exists for this user
        redemptions = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).all()
        )
        assert len(redemptions) == 1
        assert redemptions[0].referral_id == referral1.id

    @pytest.mark.unit
    async def test_apply_referral_code_unauthenticated(self, client: AsyncClient):
        """Test that unauthenticated request fails."""
        response = await client.post(
            "/api/referrals/apply",
            json={"referral_code": "TESTCODE"},
        )
        assert response.status_code == 401


class TestValidateReferralCode:
    """Tests for GET /api/referrals/validate/{code} endpoint."""

    @pytest.mark.unit
    async def test_validate_referral_code_valid(
        self,
        client: AsyncClient,
        test_referral: Referral,
    ):
        """Test validating a valid referral code."""
        response = await client.get("/api/referrals/validate/TESTCODE")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["valid"] is True
        assert data["code"] == "TESTCODE"

    @pytest.mark.unit
    async def test_validate_referral_code_invalid(
        self,
        client: AsyncClient,
    ):
        """Test validating an invalid referral code."""
        response = await client.get("/api/referrals/validate/INVALID")

        assert response.status_code == 200
        response_json = response.json()
        data = response_json["data"]
        assert data["valid"] is False
        assert data["code"] is None
