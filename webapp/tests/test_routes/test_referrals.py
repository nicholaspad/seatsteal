"""Tests for referral API routes."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from models.user import Profile
from models.referral import Referral
from models.referral_redemption import ReferralRedemption
from models.college import College
from models.stripe_customer import StripeCustomer
from utils.referral_trials import (
    ReferralTrialAction,
    ReferralTrialOutcome,
    ReferralTrialPlan,
    ReferralTrialResult,
    REFEREE_PAST_DUE_MESSAGE,
)


CREATE_PLAN = ReferralTrialPlan(action=ReferralTrialAction.CREATE)
FAILED_PLAN = ReferralTrialPlan(action=ReferralTrialAction.FAILED)


def _granted(sub_id: str) -> ReferralTrialResult:
    return ReferralTrialResult(
        outcome=ReferralTrialOutcome.GRANTED, subscription_id=sub_id
    )


@contextmanager
def mock_referral_trials(
    *,
    referee_plan=CREATE_PLAN,
    referrer_plan=CREATE_PLAN,
    referee_result=None,
    referrer_result=None,
):
    if referee_result is None:
        referee_result = _granted("sub_referee_123")
    if referrer_result is None:
        referrer_result = _granted("sub_referrer_123")

    async def plan_side(user_id, db):
        # First call in a request is the referee, second is the referrer.
        # Extra calls (retries in the same test) reuse the pair.
        plan_side.calls += 1
        if plan_side.calls % 2 == 1:
            return referee_plan
        return referrer_plan

    plan_side.calls = 0

    async def apply_side(user_id, redemption, db, *, role, plan):
        if role == "referee":
            return referee_result
        return referrer_result

    with patch(
        "api.routes.referrals.plan_referral_trial", new_callable=AsyncMock
    ) as mock_plan, patch(
        "api.routes.referrals.apply_referral_trial", new_callable=AsyncMock
    ) as mock_apply:
        mock_plan.side_effect = plan_side
        mock_apply.side_effect = apply_side
        yield mock_plan, mock_apply


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

        with mock_referral_trials():
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

        with mock_referral_trials():
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

    @pytest.mark.unit
    async def test_apply_rollback_on_referee_trial_failure(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test that database rolls back when referee trial creation fails."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(referee_plan=FAILED_PLAN):
            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        # Should return 500 error
        assert response.status_code == 500
        assert "Failed to create your trial" in response.json()["detail"]

        # Verify NO redemption was created (database rollback)
        redemption = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).first()
        )
        assert redemption is None

    @pytest.mark.unit
    async def test_apply_rollback_on_referrer_trial_failure(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test that database rolls back when referrer trial creation fails."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(referrer_plan=FAILED_PLAN):
            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        # Should return 500 error
        assert response.status_code == 500
        assert "Failed to create referrer trial" in response.json()["detail"]

        # Verify NO redemption was created (database rollback)
        redemption = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).first()
        )
        assert redemption is None

    @pytest.mark.unit
    async def test_apply_rollback_on_both_trials_fail(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test that database rolls back when both trial creations fail."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(referee_plan=FAILED_PLAN, referrer_plan=FAILED_PLAN):
            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        # Should return 500 error
        assert response.status_code == 500

        # Verify NO redemption was created (database rollback)
        redemption = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).first()
        )
        assert redemption is None

    @pytest.mark.unit
    async def test_apply_success_both_trials_succeed(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test successful application when both trials succeed."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(), patch(
            "api.routes.referrals.invalidate_user_caches"
        ) as mock_invalidate:
            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        # Should return 200 success
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify redemption WAS created and committed
        redemption = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).first()
        )
        assert redemption is not None
        assert redemption.referral_id == referral.id

        # Verify both trial subscription IDs were stored
        # Note: The IDs are stored in the redemption record by the trial creation functions,
        # but in this test we're mocking those functions, so we can't verify the IDs here.
        # The actual storage is tested in test_utils/test_referral_trials.py

    @pytest.mark.unit
    async def test_apply_invalidates_caches_for_both_users(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test that caches are invalidated for both referee and referrer."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(), patch(
            "api.routes.referrals.invalidate_user_caches"
        ) as mock_invalidate:
            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        assert response.status_code == 200

        # Verify cache invalidation was called exactly twice
        assert mock_invalidate.call_count == 2

        # Verify it was called with correct user IDs
        call_args = [call[0][0] for call in mock_invalidate.call_args_list]
        assert str(test_user.id) in call_args  # Referee
        assert str(second_user.id) in call_args  # Referrer

    @pytest.mark.unit
    async def test_apply_sends_referral_emails_to_both_users(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test that referral success emails are sent to both referee and referrer."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(), patch(
            "api.routes.referrals.EmailService"
        ) as mock_email_service_class:
            # Set up mock email service instance
            mock_email_service = MagicMock()
            mock_email_service.send_referral_success_email = AsyncMock(
                return_value=True
            )
            mock_email_service_class.return_value = mock_email_service

            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        assert response.status_code == 200

        # Verify email service was instantiated
        mock_email_service_class.assert_called_once()

        # Verify send_referral_success_email was called twice (for referee and referrer)
        assert mock_email_service.send_referral_success_email.call_count == 2

        # Verify referee email was sent with correct parameters
        referee_call = mock_email_service.send_referral_success_email.call_args_list[0]
        assert referee_call[1]["to_email"] == test_user.email
        assert referee_call[1]["other_user_email"] == second_user.email
        assert referee_call[1]["is_referrer"] is False
        assert referee_call[1]["tier_name"] == "Pro"  # Default

        # Verify referrer email was sent with correct parameters
        referrer_call = mock_email_service.send_referral_success_email.call_args_list[1]
        assert referrer_call[1]["to_email"] == second_user.email
        assert referrer_call[1]["other_user_email"] == test_user.email
        assert referrer_call[1]["is_referrer"] is True
        assert referrer_call[1]["tier_name"] == "Pro"  # Default

    @pytest.mark.unit
    async def test_apply_email_failure_does_not_break_referral(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test that email failures don't prevent successful referral application."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(), patch(
            "api.routes.referrals.EmailService"
        ) as mock_email_service_class:
            # Set up mock email service to raise exception
            mock_email_service = MagicMock()
            mock_email_service.send_referral_success_email = AsyncMock(
                side_effect=Exception("Email service down")
            )
            mock_email_service_class.return_value = mock_email_service

            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        # Should still succeed despite email failure
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify redemption was still created
        redemption = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).first()
        )
        assert redemption is not None
        assert redemption.referral_id == referral.id

    @pytest.mark.unit
    async def test_apply_uses_plus_tier_name_for_plus_users(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        """Test that Plus tier name is used when user was on Plus tier."""
        # Create referral code
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        with mock_referral_trials(), patch(
            "api.routes.referrals.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "api.routes.referrals.EmailService"
        ) as mock_email_service_class:
            mock_get_tier.return_value = "plus"  # User was on Plus tier

            # Set up mock email service instance
            mock_email_service = MagicMock()
            mock_email_service.send_referral_success_email = AsyncMock(
                return_value=True
            )
            mock_email_service_class.return_value = mock_email_service

            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        assert response.status_code == 200

        # Verify referee email was sent with "Plus" tier name
        referee_call = mock_email_service.send_referral_success_email.call_args_list[0]
        assert referee_call[1]["tier_name"] == "Plus"

    @pytest.mark.unit
    async def test_past_due_referee_returns_409_with_zero_stripe_writes(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.add(
            StripeCustomer(
                user_id=test_user.id,
                stripe_customer_id="cus_referee",
                email=test_user.email,
            )
        )
        test_db.commit()

        past_due = MagicMock()
        past_due.id = "sub_referee_past_due"
        past_due.status = "past_due"
        past_due.tier = "pro"
        past_due.created = 1

        with patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.stripe_utils.stripe.Subscription.create"
        ) as mock_create, patch(
            "utils.stripe_utils.stripe.Subscription.modify"
        ) as mock_modify, patch(
            "utils.stripe_utils.stripe.Subscription.retrieve"
        ) as mock_retrieve:
            mock_list.return_value = MagicMock(data=[past_due])

            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )
            retry = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        assert response.status_code == 409
        assert response.json()["detail"] == REFEREE_PAST_DUE_MESSAGE
        assert retry.status_code == 409
        assert retry.json()["detail"] == REFEREE_PAST_DUE_MESSAGE
        mock_create.assert_not_called()
        mock_modify.assert_not_called()
        mock_retrieve.assert_not_called()
        redemption = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).first()
        )
        assert redemption is None

    @pytest.mark.unit
    async def test_past_due_referrer_grants_referee_and_saves_skipped_redemption(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        second_user: Profile,
    ):
        referral = Referral(
            referrer_id=second_user.id,
            referral_code="TESTCODE",
        )
        test_db.add(referral)
        test_db.add(
            StripeCustomer(
                user_id=test_user.id,
                stripe_customer_id="cus_referee",
                email=test_user.email,
            )
        )
        test_db.add(
            StripeCustomer(
                user_id=second_user.id,
                stripe_customer_id="cus_referrer",
                email=second_user.email,
            )
        )
        test_db.commit()

        past_due = MagicMock()
        past_due.id = "sub_referrer_past_due"
        past_due.status = "past_due"
        past_due.tier = "pro"
        past_due.created = 1

        def list_side_effect(customer=None, **_kwargs):
            if customer == "cus_referrer":
                return MagicMock(data=[past_due])
            return MagicMock(data=[])

        created = MagicMock()
        created.id = "sub_referee_new"
        created.trial_end = int(
            (datetime.now(timezone.utc) + timedelta(days=7)).timestamp()
        )

        with patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.stripe_utils.stripe.Subscription.create"
        ) as mock_create, patch(
            "utils.stripe_utils.stripe.Subscription.modify"
        ) as mock_modify, patch(
            "utils.stripe_utils.stripe.Subscription.retrieve"
        ) as mock_retrieve:
            mock_list.side_effect = list_side_effect
            mock_create.return_value = created

            response = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

            assert response.status_code == 200
            mock_create.assert_called_once()
            mock_modify.assert_not_called()
            mock_retrieve.assert_not_called()

            redemption = (
                test_db.query(ReferralRedemption)
                .filter_by(referee_id=test_user.id)
                .first()
            )
            assert redemption is not None
            assert redemption.referee_trial_subscription_id == "sub_referee_new"
            # Skipped referrer reuses nullable referrer_trial_subscription_id.
            assert redemption.referrer_trial_subscription_id is None

            retry = await authenticated_client.post(
                "/api/referrals/apply",
                json={"referral_code": "TESTCODE"},
            )

        assert retry.status_code == 400
        assert "already claimed a referral code" in retry.json()["detail"].lower()
        assert mock_create.call_count == 1
        redemptions = (
            test_db.query(ReferralRedemption).filter_by(referee_id=test_user.id).all()
        )
        assert len(redemptions) == 1


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
