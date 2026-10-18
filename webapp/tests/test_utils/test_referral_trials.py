"""Tests for referral trial creation utility functions."""

import logging
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from sqlalchemy.orm import Session

from models.user import Profile
from models.referral import Referral
from models.referral_redemption import ReferralRedemption
from models.stripe_customer import StripeCustomer
from models.college import College
from utils.referral_trials import (
    ReferralTrialOutcome,
    create_referee_trial,
    create_referrer_trial,
    referral_idempotency_key,
)


def _assert_granted(result, sub_id: str) -> None:
    assert result.outcome == ReferralTrialOutcome.GRANTED
    assert result.subscription_id == sub_id


def _assert_skipped(result) -> None:
    assert result.outcome == ReferralTrialOutcome.SKIPPED_PAST_DUE
    assert result.subscription_id is None


def _assert_failed(result) -> None:
    assert result.outcome == ReferralTrialOutcome.FAILED
    assert result.subscription_id is None


def _assert_extend_called(mock_extend, sub_id, referee_id, role: str) -> None:
    mock_extend.assert_called_once_with(
        sub_id,
        additional_days=7,
        idempotency_key=referral_idempotency_key(referee_id, role),
    )


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
def test_redemption(
    test_db: Session, test_user: Profile, test_referral: Referral
) -> ReferralRedemption:
    """Create a test referral redemption record."""
    redemption = ReferralRedemption(
        referral_id=test_referral.id,
        referee_id=test_user.id,
    )
    test_db.add(redemption)
    test_db.commit()
    test_db.refresh(redemption)
    return redemption


@pytest.fixture
def test_stripe_customer(test_db: Session, test_user: Profile) -> StripeCustomer:
    """Create a test Stripe customer."""
    customer = StripeCustomer(
        user_id=test_user.id,
        stripe_customer_id="cus_test123",
        email=test_user.email,
    )
    test_db.add(customer)
    test_db.commit()
    test_db.refresh(customer)
    return customer


class TestCreateRefereeTrial:
    """Tests for create_referee_trial function."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_trial_no_subscription_success(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test creating Pro trial when user has no subscription."""
        # Mock subscription list to return empty (no subscriptions)
        mock_sub_list = MagicMock()
        mock_sub_list.data = []

        # Mock trial subscription creation
        mock_trial_sub = MagicMock()
        mock_trial_sub.id = "sub_trial_123"
        mock_trial_sub.trial_end = int((datetime.now() + timedelta(days=7)).timestamp())

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.return_value = mock_trial_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Assertions
            _assert_granted(result, "sub_trial_123")
            assert test_redemption.referee_trial_subscription_id == "sub_trial_123"
            assert test_redemption.referee_trial_end is not None

            # Verify create_trial_subscription was called with correct params
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["customer_id"] == "cus_test123"
            assert call_kwargs["tier"] == "pro"
            assert call_kwargs["trial_days"] == 7
            assert call_kwargs["idempotency_key"] == referral_idempotency_key(
                test_user.id, "referee"
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_active_plus_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending trial for user with active Plus subscription."""
        # Mock existing Plus subscription
        mock_plus_sub = MagicMock()
        mock_plus_sub.id = "sub_plus_123"
        mock_plus_sub.status = "active"
        mock_plus_sub.items.data = [MagicMock()]
        mock_plus_sub.items.data[0].price.id = "price_plus"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_plus_sub]

        # Mock extended subscription
        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_plus_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Assertions
            _assert_granted(result, "sub_plus_123")
            assert test_redemption.referee_trial_subscription_id == "sub_plus_123"

            # Verify extend was called (NOT create)
            _assert_extend_called(mock_extend, "sub_plus_123", test_user.id, "referee")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_active_pro_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending trial for user with active Pro subscription."""
        # Mock existing Pro subscription
        mock_pro_sub = MagicMock()
        mock_pro_sub.id = "sub_pro_123"
        mock_pro_sub.status = "active"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_pro_sub]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_pro_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_pro_123")
            _assert_extend_called(mock_extend, "sub_pro_123", test_user.id, "referee")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_trialing_plus_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending trial for user with trialing Plus subscription."""
        # Mock trialing Plus subscription
        mock_trialing_sub = MagicMock()
        mock_trialing_sub.id = "sub_trial_plus_123"
        mock_trialing_sub.status = "trialing"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_trialing_sub]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_trial_plus_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Assert trialing subscription was extended (NO upgrade to Pro)
            _assert_granted(result, "sub_trial_plus_123")
            _assert_extend_called(
                mock_extend, "sub_trial_plus_123", test_user.id, "referee"
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_trialing_pro_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending trial for user with trialing Pro subscription."""
        mock_trialing_sub = MagicMock()
        mock_trialing_sub.id = "sub_trial_pro_123"
        mock_trialing_sub.status = "trialing"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_trialing_sub]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_trial_pro_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_trial_pro_123")
            _assert_extend_called(
                mock_extend, "sub_trial_pro_123", test_user.id, "referee"
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stripe_customer_creation_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
    ):
        """Test graceful handling when Stripe customer creation fails."""
        with patch(
            "utils.referral_trials.create_stripe_customer", new_callable=AsyncMock
        ) as mock_create_customer:
            mock_create_customer.side_effect = Exception("Stripe customer error")

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            _assert_failed(result)
            assert test_redemption.referee_trial_subscription_id is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_trial_creation_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test graceful handling when trial subscription creation fails."""
        mock_sub_list = MagicMock()
        mock_sub_list.data = []

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.side_effect = Exception("Stripe API error")

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Should return None and not raise exception
            _assert_failed(result)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_trial_extension_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test graceful handling when trial extension fails."""
        mock_sub = MagicMock()
        mock_sub.id = "sub_123"
        mock_sub.status = "active"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_sub]

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.side_effect = Exception("Stripe API error")

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            _assert_failed(result)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_multiple_active_subscriptions_picks_pro_over_plus(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """When Plus and Pro are both active, extend Pro even if Plus is newer."""
        mock_plus = MagicMock()
        mock_plus.id = "sub_plus_newer"
        mock_plus.status = "active"
        mock_plus.tier = "plus"
        mock_plus.created = 200

        mock_pro = MagicMock()
        mock_pro.id = "sub_pro_older"
        mock_pro.status = "active"
        mock_pro.tier = "pro"
        mock_pro.created = 50

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_plus, mock_pro]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_pro_older"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_pro_older")
            _assert_extend_called(mock_extend, "sub_pro_older", test_user.id, "referee")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_past_due_subscription_skips_without_create_or_extend(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
        caplog,
    ):
        mock_past_due = MagicMock()
        mock_past_due.id = "sub_past_due_123"
        mock_past_due.status = "past_due"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_past_due]

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list

            with caplog.at_level(logging.WARNING):
                result = await create_referee_trial(
                    test_user.id, test_redemption, test_db
                )

            _assert_skipped(result)
            mock_extend.assert_not_called()
            mock_create.assert_not_called()
            assert "past_due" in caplog.text
            assert "sub_past_due_123" in caplog.text
            assert str(test_user.id) in caplog.text

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_active_plus_past_due_extends_the_active_sub(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """past_due skip must not fire when an extendable sub is also present."""
        mock_past_due = MagicMock()
        mock_past_due.id = "sub_past_due_123"
        mock_past_due.status = "past_due"
        mock_past_due.tier = "plus"
        mock_past_due.created = 200

        mock_active = MagicMock()
        mock_active.id = "sub_active_pro"
        mock_active.status = "active"
        mock_active.tier = "pro"
        mock_active.created = 50

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_past_due, mock_active]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_active_pro"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_active_pro")
            _assert_extend_called(
                mock_extend, "sub_active_pro", test_user.id, "referee"
            )
            mock_create.assert_not_called()


class TestCreateReferrerTrial:
    """Tests for create_referrer_trial function."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_trial_free_tier_success(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test creating Pro trial for referrer on free tier."""
        mock_sub_list = MagicMock()
        mock_sub_list.data = []

        mock_trial_sub = MagicMock()
        mock_trial_sub.id = "sub_referrer_trial_123"
        mock_trial_sub.trial_end = int((datetime.now() + timedelta(days=7)).timestamp())

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create, patch(
            "utils.referral_trials.invalidate_user_caches"
        ) as mock_invalidate:

            mock_get_tier.return_value = "free"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.return_value = mock_trial_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            # Assertions
            _assert_granted(result, "sub_referrer_trial_123")
            assert (
                test_redemption.referrer_trial_subscription_id
                == "sub_referrer_trial_123"
            )
            assert test_redemption.referrer_previous_tier == "free"
            assert test_redemption.referrer_trial_end is not None

            # Verify cache was invalidated
            mock_invalidate.assert_called_once_with(test_user.id)

            # Verify create_trial_subscription was called with correct params
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["tier"] == "pro"
            assert call_kwargs["trial_days"] == 7
            assert call_kwargs["idempotency_key"] == referral_idempotency_key(
                test_user.id, "referrer"
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_active_plus_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending Plus subscription (NO upgrade to Pro)."""
        mock_plus_sub = MagicMock()
        mock_plus_sub.id = "sub_plus_123"
        mock_plus_sub.status = "active"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_plus_sub]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_plus_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.invalidate_user_caches"
        ) as mock_invalidate:

            mock_get_tier.return_value = "plus"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            # Assert Plus subscription was extended (NO upgrade to Pro)
            _assert_granted(result, "sub_plus_123")
            assert test_redemption.referrer_previous_tier == "plus"
            _assert_extend_called(mock_extend, "sub_plus_123", test_user.id, "referrer")
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_multiple_active_subscriptions_picks_pro_over_plus(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """When Plus and Pro are both active, extend Pro even if Plus is newer."""
        mock_plus = MagicMock()
        mock_plus.id = "sub_plus_newer"
        mock_plus.status = "active"
        mock_plus.tier = "plus"
        mock_plus.created = 200

        mock_pro = MagicMock()
        mock_pro.id = "sub_pro_older"
        mock_pro.status = "active"
        mock_pro.tier = "pro"
        mock_pro.created = 50

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_plus, mock_pro]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_pro_older"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.invalidate_user_caches"
        ):

            mock_get_tier.return_value = "pro"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_pro_older")
            _assert_extend_called(
                mock_extend, "sub_pro_older", test_user.id, "referrer"
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_active_pro_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending Pro subscription."""
        mock_pro_sub = MagicMock()
        mock_pro_sub.id = "sub_pro_123"
        mock_pro_sub.status = "active"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_pro_sub]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_pro_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.invalidate_user_caches"
        ) as mock_invalidate:

            mock_get_tier.return_value = "pro"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_pro_123")
            assert test_redemption.referrer_previous_tier == "pro"
            _assert_extend_called(mock_extend, "sub_pro_123", test_user.id, "referrer")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_trialing_plus_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending trialing Plus subscription (NO upgrade)."""
        mock_trialing_sub = MagicMock()
        mock_trialing_sub.id = "sub_trial_plus_123"
        mock_trialing_sub.status = "trialing"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_trialing_sub]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_trial_plus_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.invalidate_user_caches"
        ) as mock_invalidate:

            mock_get_tier.return_value = "plus"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            # Assert trialing Plus was extended (NO upgrade)
            _assert_granted(result, "sub_trial_plus_123")
            _assert_extend_called(
                mock_extend, "sub_trial_plus_123", test_user.id, "referrer"
            )
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extend_trial_trialing_pro_subscription(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test extending trialing Pro subscription."""
        mock_trialing_sub = MagicMock()
        mock_trialing_sub.id = "sub_trial_pro_123"
        mock_trialing_sub.status = "trialing"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_trialing_sub]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_trial_pro_123"
        mock_extended_sub.trial_end = int(
            (datetime.now() + timedelta(days=14)).timestamp()
        )

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.invalidate_user_caches"
        ) as mock_invalidate:

            mock_get_tier.return_value = "pro"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_trial_pro_123")
            _assert_extend_called(
                mock_extend, "sub_trial_pro_123", test_user.id, "referrer"
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_free_tier_no_subscription_creates_trial(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test that free tier with no Stripe subscription creates new trial."""
        mock_sub_list = MagicMock()
        mock_sub_list.data = []

        mock_trial_sub = MagicMock()
        mock_trial_sub.id = "sub_trial_123"
        mock_trial_sub.trial_end = int((datetime.now() + timedelta(days=7)).timestamp())

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create, patch(
            "utils.referral_trials.invalidate_user_caches"
        ) as mock_invalidate:

            mock_get_tier.return_value = "free"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.return_value = mock_trial_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            _assert_granted(result, "sub_trial_123")
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stripe_customer_creation_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
    ):
        """Test graceful handling when Stripe customer creation fails."""
        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.create_stripe_customer", new_callable=AsyncMock
        ) as mock_create_customer:

            mock_get_tier.return_value = "free"
            mock_create_customer.side_effect = Exception("Stripe customer error")

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            _assert_failed(result)
            assert test_redemption.referrer_trial_subscription_id is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_trial_creation_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test graceful handling when trial creation fails."""
        mock_sub_list = MagicMock()
        mock_sub_list.data = []

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create:

            mock_get_tier.return_value = "free"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.side_effect = Exception("Stripe API error")

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            _assert_failed(result)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_trial_extension_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test graceful handling when trial extension fails."""
        mock_sub = MagicMock()
        mock_sub.id = "sub_123"
        mock_sub.status = "active"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_sub]

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend:

            mock_get_tier.return_value = "plus"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.side_effect = Exception("Stripe API error")

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            _assert_failed(result)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stores_previous_tier_correctly(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test that referrer_previous_tier is stored correctly for all tiers."""
        mock_sub_list = MagicMock()
        mock_sub_list.data = []

        mock_trial_sub = MagicMock()
        mock_trial_sub.id = "sub_trial_123"
        mock_trial_sub.trial_end = int((datetime.now() + timedelta(days=7)).timestamp())

        # Test all tiers
        for tier in ["free", "plus", "pro"]:
            # Reset redemption
            test_redemption.referrer_previous_tier = None

            with patch(
                "utils.referral_trials.get_user_subscription_tier"
            ) as mock_get_tier, patch(
                "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
            ) as mock_get_customer, patch(
                "utils.referral_trials.stripe.Subscription.list"
            ) as mock_list, patch(
                "utils.referral_trials.create_trial_subscription",
                new_callable=AsyncMock,
            ) as mock_create, patch(
                "utils.referral_trials.invalidate_user_caches"
            ) as mock_invalidate:

                mock_get_tier.return_value = tier
                mock_get_customer.return_value = test_stripe_customer
                mock_list.return_value = mock_sub_list
                mock_create.return_value = mock_trial_sub

                await create_referrer_trial(test_user.id, test_redemption, test_db)

                # Assert tier was stored correctly
                assert test_redemption.referrer_previous_tier == tier

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_past_due_subscription_skips_without_create_or_extend(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
        caplog,
    ):
        mock_past_due = MagicMock()
        mock_past_due.id = "sub_past_due_456"
        mock_past_due.status = "past_due"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_past_due]

        with patch(
            "utils.referral_trials.get_user_subscription_tier"
        ) as mock_get_tier, patch(
            "utils.referral_trials.get_stripe_customer", new_callable=AsyncMock
        ) as mock_get_customer, patch(
            "utils.referral_trials.stripe.Subscription.list"
        ) as mock_list, patch(
            "utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock
        ) as mock_extend, patch(
            "utils.referral_trials.create_trial_subscription", new_callable=AsyncMock
        ) as mock_create, patch(
            "utils.referral_trials.invalidate_user_caches"
        ):

            mock_get_tier.return_value = "pro"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list

            with caplog.at_level(logging.WARNING):
                result = await create_referrer_trial(
                    test_user.id, test_redemption, test_db
                )

            _assert_skipped(result)
            mock_extend.assert_not_called()
            mock_create.assert_not_called()
            assert "past_due" in caplog.text
            assert "sub_past_due_456" in caplog.text
            assert str(test_user.id) in caplog.text


def _make_stripe_sub(
    sub_id,
    status,
    *,
    tier="pro",
    trial_end=None,
    created=1_700_000_000,
):
    sub = MagicMock()
    sub.id = sub_id
    sub.status = status
    sub.tier = tier
    sub.created = created
    sub.trial_end = trial_end
    return sub


def _modify_returns_kwargs(sub_id, **kwargs):
    out = MagicMock()
    out.id = sub_id
    out.trial_end = kwargs["trial_end"]
    return out


class TestReferralTrialStripeSdkParams:
    """Assert Stripe SDK call params (not the extend_subscription_trial helper)."""

    def _sdk_patches(self):
        return (
            patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock),
            patch("utils.referral_trials.stripe.Subscription.list"),
            patch("utils.stripe_utils.stripe.Subscription.retrieve"),
            patch("utils.stripe_utils.stripe.Subscription.modify"),
            patch("utils.stripe_utils.stripe.Subscription.create"),
            patch("utils.referral_trials.get_user_subscription_tier"),
            patch("utils.referral_trials.invalidate_user_caches"),
        )

    async def _run_role(self, role, test_user, test_redemption, test_db, mocks):
        if role == "referee":
            return await create_referee_trial(test_user.id, test_redemption, test_db)
        return await create_referrer_trial(test_user.id, test_redemption, test_db)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.parametrize("role", ["referee", "referrer"])
    async def test_past_due_makes_zero_modify_and_create_calls(
        self,
        role,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
        caplog,
    ):
        past_due = _make_stripe_sub("sub_past_due_sdk", "past_due")
        (
            mock_get_customer,
            mock_list,
            mock_retrieve,
            mock_modify,
            mock_create,
            mock_get_tier,
            _mock_invalidate,
        ) = self._sdk_patches()

        with mock_get_customer as get_customer, mock_list as listed, mock_retrieve as retrieve, mock_modify as modify, mock_create as create, mock_get_tier as get_tier, (
            _mock_invalidate
        ):
            get_customer.return_value = test_stripe_customer
            get_tier.return_value = "pro"
            listed.return_value = MagicMock(data=[past_due])

            with caplog.at_level(logging.WARNING):
                result = await self._run_role(
                    role, test_user, test_redemption, test_db, None
                )

            _assert_skipped(result)
            modify.assert_not_called()
            create.assert_not_called()
            retrieve.assert_not_called()
            assert "past_due" in caplog.text
            assert "sub_past_due_sdk" in caplog.text
            assert str(test_user.id) in caplog.text

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.parametrize("role", ["referee", "referrer"])
    @pytest.mark.parametrize("status", ["active", "trialing"])
    async def test_active_or_trialing_modifies_with_proration_none(
        self,
        role,
        status,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        future = datetime.now(timezone.utc) + timedelta(days=4)
        trial_end_ts = int(future.timestamp())
        existing = _make_stripe_sub(f"sub_{status}_sdk", status, trial_end=trial_end_ts)
        (
            mock_get_customer,
            mock_list,
            mock_retrieve,
            mock_modify,
            mock_create,
            mock_get_tier,
            _mock_invalidate,
        ) = self._sdk_patches()

        with mock_get_customer as get_customer, mock_list as listed, mock_retrieve as retrieve, mock_modify as modify, mock_create as create, mock_get_tier as get_tier, (
            _mock_invalidate
        ):
            get_customer.return_value = test_stripe_customer
            get_tier.return_value = "pro"
            listed.return_value = MagicMock(data=[existing])
            retrieve.return_value = existing
            modify.side_effect = _modify_returns_kwargs

            result = await self._run_role(
                role, test_user, test_redemption, test_db, None
            )

            _assert_granted(result, f"sub_{status}_sdk")
            modify.assert_called_once()
            create.assert_not_called()
            kwargs = modify.call_args.kwargs
            assert kwargs["proration_behavior"] == "none"
            assert kwargs["idempotency_key"] == referral_idempotency_key(
                test_user.id, role
            )
            expected = datetime.fromtimestamp(
                trial_end_ts, tz=timezone.utc
            ) + timedelta(days=7)
            actual = datetime.fromtimestamp(kwargs["trial_end"], tz=timezone.utc)
            assert abs((actual - expected).total_seconds()) < 2
            assert modify.call_args.args[0] == f"sub_{status}_sdk"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_expired_trial_end_starts_from_now_plus_seven_days(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        expired = datetime.now(timezone.utc) - timedelta(days=30)
        existing = _make_stripe_sub(
            "sub_expired_sdk", "active", trial_end=int(expired.timestamp())
        )
        (
            mock_get_customer,
            mock_list,
            mock_retrieve,
            mock_modify,
            mock_create,
            mock_get_tier,
            _mock_invalidate,
        ) = self._sdk_patches()

        with mock_get_customer as get_customer, mock_list as listed, mock_retrieve as retrieve, mock_modify as modify, mock_create as create, (
            mock_get_tier
        ), _mock_invalidate:
            get_customer.return_value = test_stripe_customer
            listed.return_value = MagicMock(data=[existing])
            retrieve.return_value = existing
            modify.side_effect = _modify_returns_kwargs

            before = datetime.now(timezone.utc)
            result = await create_referee_trial(test_user.id, test_redemption, test_db)
            after = datetime.now(timezone.utc)

            _assert_granted(result, "sub_expired_sdk")
            create.assert_not_called()
            kwargs = modify.call_args.kwargs
            assert kwargs["proration_behavior"] == "none"
            assert kwargs["idempotency_key"] == referral_idempotency_key(
                test_user.id, "referee"
            )
            new_end = datetime.fromtimestamp(kwargs["trial_end"], tz=timezone.utc)
            assert new_end >= before + timedelta(days=7) - timedelta(seconds=1)
            assert new_end <= after + timedelta(days=7)
            assert new_end > expired + timedelta(days=8)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.parametrize("role", ["referee", "referrer"])
    async def test_create_passes_idempotency_key(
        self,
        role,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        created = MagicMock()
        created.id = "sub_created_sdk"
        created.trial_end = int(
            (datetime.now(timezone.utc) + timedelta(days=7)).timestamp()
        )
        (
            mock_get_customer,
            mock_list,
            mock_retrieve,
            mock_modify,
            mock_create,
            mock_get_tier,
            _mock_invalidate,
        ) = self._sdk_patches()

        with mock_get_customer as get_customer, mock_list as listed, mock_retrieve as retrieve, mock_modify as modify, mock_create as create, mock_get_tier as get_tier, (
            _mock_invalidate
        ):
            get_customer.return_value = test_stripe_customer
            get_tier.return_value = "free"
            listed.return_value = MagicMock(data=[])
            create.return_value = created

            result = await self._run_role(
                role, test_user, test_redemption, test_db, None
            )

            _assert_granted(result, "sub_created_sdk")
            modify.assert_not_called()
            retrieve.assert_not_called()
            create.assert_called_once()
            assert create.call_args.kwargs[
                "idempotency_key"
            ] == referral_idempotency_key(test_user.id, role)
