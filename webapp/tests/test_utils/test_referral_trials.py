"""Tests for referral trial creation utility functions."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from sqlalchemy.orm import Session

from models.user import Profile
from models.referral import Referral
from models.referral_redemption import ReferralRedemption
from models.stripe_customer import StripeCustomer
from models.college import College
from utils.referral_trials import create_referee_trial, create_referrer_trial


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

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.create_trial_subscription", new_callable=AsyncMock) as mock_create:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.return_value = mock_trial_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Assertions
            assert result == "sub_trial_123"
            assert test_redemption.referee_trial_subscription_id == "sub_trial_123"
            assert test_redemption.referee_trial_end is not None

            # Verify create_trial_subscription was called with correct params
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["customer_id"] == "cus_test123"
            assert call_kwargs["tier"] == "pro"
            assert call_kwargs["trial_days"] == 7

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Assertions
            assert result == "sub_plus_123"
            assert test_redemption.referee_trial_subscription_id == "sub_plus_123"

            # Verify extend was called (NOT create)
            mock_extend.assert_called_once_with("sub_plus_123", additional_days=7)

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            assert result == "sub_pro_123"
            mock_extend.assert_called_once_with("sub_pro_123", additional_days=7)

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Assert trialing subscription was extended (NO upgrade to Pro)
            assert result == "sub_trial_plus_123"
            mock_extend.assert_called_once_with("sub_trial_plus_123", additional_days=7)

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            assert result == "sub_trial_pro_123"
            mock_extend.assert_called_once_with("sub_trial_pro_123", additional_days=7)

    @pytest.mark.unit
    async def test_stripe_customer_creation_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
    ):
        """Test graceful handling when Stripe customer creation fails."""
        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer:
            mock_get_customer.return_value = None

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Should return None and not raise exception
            assert result is None
            assert test_redemption.referee_trial_subscription_id is None

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

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.create_trial_subscription", new_callable=AsyncMock) as mock_create:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.side_effect = Exception("Stripe API error")

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Should return None and not raise exception
            assert result is None

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

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.side_effect = Exception("Stripe API error")

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            assert result is None

    @pytest.mark.unit
    async def test_multiple_active_subscriptions_uses_first(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
        test_stripe_customer: StripeCustomer,
    ):
        """Test that when user has multiple subscriptions, the first one is used."""
        mock_sub1 = MagicMock()
        mock_sub1.id = "sub_first_123"
        mock_sub1.status = "active"

        mock_sub2 = MagicMock()
        mock_sub2.id = "sub_second_456"
        mock_sub2.status = "active"

        mock_sub_list = MagicMock()
        mock_sub_list.data = [mock_sub1, mock_sub2]

        mock_extended_sub = MagicMock()
        mock_extended_sub.id = "sub_first_123"
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend:

            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referee_trial(test_user.id, test_redemption, test_db)

            # Should use the first subscription
            assert result == "sub_first_123"
            mock_extend.assert_called_once_with("sub_first_123", additional_days=7)


class TestCreateReferrerTrial:
    """Tests for create_referrer_trial function."""

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

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.create_trial_subscription", new_callable=AsyncMock) as mock_create, \
             patch("utils.referral_trials.invalidate_user_caches") as mock_invalidate:

            mock_get_tier.return_value = "free"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.return_value = mock_trial_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            # Assertions
            assert result == "sub_referrer_trial_123"
            assert test_redemption.referrer_trial_subscription_id == "sub_referrer_trial_123"
            assert test_redemption.referrer_previous_tier == "free"
            assert test_redemption.referrer_trial_end is not None

            # Verify cache was invalidated
            mock_invalidate.assert_called_once_with(test_user.id)

            # Verify create_trial_subscription was called with correct params
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["tier"] == "pro"
            assert call_kwargs["trial_days"] == 7

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend, \
             patch("utils.referral_trials.invalidate_user_caches") as mock_invalidate:

            mock_get_tier.return_value = "plus"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            # Assert Plus subscription was extended (NO upgrade to Pro)
            assert result == "sub_plus_123"
            assert test_redemption.referrer_previous_tier == "plus"
            mock_extend.assert_called_once_with("sub_plus_123", additional_days=7)
            mock_invalidate.assert_called_once()

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend, \
             patch("utils.referral_trials.invalidate_user_caches") as mock_invalidate:

            mock_get_tier.return_value = "pro"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            assert result == "sub_pro_123"
            assert test_redemption.referrer_previous_tier == "pro"
            mock_extend.assert_called_once_with("sub_pro_123", additional_days=7)

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend, \
             patch("utils.referral_trials.invalidate_user_caches") as mock_invalidate:

            mock_get_tier.return_value = "plus"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            # Assert trialing Plus was extended (NO upgrade)
            assert result == "sub_trial_plus_123"
            mock_extend.assert_called_once_with("sub_trial_plus_123", additional_days=7)
            mock_invalidate.assert_called_once()

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
        mock_extended_sub.trial_end = int((datetime.now() + timedelta(days=14)).timestamp())

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend, \
             patch("utils.referral_trials.invalidate_user_caches") as mock_invalidate:

            mock_get_tier.return_value = "pro"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.return_value = mock_extended_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            assert result == "sub_trial_pro_123"
            mock_extend.assert_called_once_with("sub_trial_pro_123", additional_days=7)

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

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.create_trial_subscription", new_callable=AsyncMock) as mock_create, \
             patch("utils.referral_trials.invalidate_user_caches") as mock_invalidate:

            mock_get_tier.return_value = "free"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.return_value = mock_trial_sub

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            assert result == "sub_trial_123"
            mock_create.assert_called_once()

    @pytest.mark.unit
    async def test_stripe_customer_creation_fails(
        self,
        test_db: Session,
        test_user: Profile,
        test_redemption: ReferralRedemption,
    ):
        """Test graceful handling when Stripe customer creation fails."""
        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer:

            mock_get_tier.return_value = "free"
            mock_get_customer.return_value = None

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            assert result is None
            assert test_redemption.referrer_trial_subscription_id is None

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

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.create_trial_subscription", new_callable=AsyncMock) as mock_create:

            mock_get_tier.return_value = "free"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_create.side_effect = Exception("Stripe API error")

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            assert result is None

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

        with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
             patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
             patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
             patch("utils.referral_trials.extend_subscription_trial", new_callable=AsyncMock) as mock_extend:

            mock_get_tier.return_value = "plus"
            mock_get_customer.return_value = test_stripe_customer
            mock_list.return_value = mock_sub_list
            mock_extend.side_effect = Exception("Stripe API error")

            result = await create_referrer_trial(test_user.id, test_redemption, test_db)

            assert result is None

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

            with patch("utils.referral_trials.get_user_subscription_tier", new_callable=AsyncMock) as mock_get_tier, \
                 patch("utils.referral_trials.get_stripe_customer", new_callable=AsyncMock) as mock_get_customer, \
                 patch("utils.referral_trials.stripe.Subscription.list") as mock_list, \
                 patch("utils.referral_trials.create_trial_subscription", new_callable=AsyncMock) as mock_create, \
                 patch("utils.referral_trials.invalidate_user_caches") as mock_invalidate:

                mock_get_tier.return_value = tier
                mock_get_customer.return_value = test_stripe_customer
                mock_list.return_value = mock_sub_list
                mock_create.return_value = mock_trial_sub

                await create_referrer_trial(test_user.id, test_redemption, test_db)

                # Assert tier was stored correctly
                assert test_redemption.referrer_previous_tier == tier
