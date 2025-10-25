"""Tests for premium subscription utilities."""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4

from webapp.utils.premium import (
    get_user_subscription_tier,
    get_user_active_subscription_count,
    get_subscription_features,
    require_premium_access,
    check_subscription_limit,
)
from webapp.models.user import Profile
from webapp.models.stripe_subscription import StripeSubscription
from webapp.models.stripe_customer import StripeCustomer
from webapp.models.subscription import Subscription
from webapp.models.class_model import Class


class TestGetUserSubscriptionTier:
    """Tests for get_user_subscription_tier function."""

    @pytest.mark.unit
    def test_no_subscription_returns_free(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that user with no subscription returns free tier."""
        tier = get_user_subscription_tier(test_user.id, test_db)
        assert tier == "free"

    @pytest.mark.unit
    def test_active_plus_subscription_returns_plus(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that user with active Plus subscription returns plus tier."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create active Plus subscription
        plus_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_plus_123",
            stripe_customer_id="cus_123",
            status="active",
            tier="plus",
            price_id="price_plus",
        )
        test_db.add(plus_sub)
        test_db.commit()

        tier = get_user_subscription_tier(test_user.id, test_db)
        assert tier == "plus"

    @pytest.mark.unit
    def test_active_pro_subscription_returns_pro(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that user with active Pro subscription returns pro tier."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_pro_123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create active Pro subscription
        pro_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_pro_123",
            stripe_customer_id="cus_pro_123",
            status="active",
            tier="pro",
            price_id="price_pro",
        )
        test_db.add(pro_sub)
        test_db.commit()

        tier = get_user_subscription_tier(test_user.id, test_db)
        assert tier == "pro"

    @pytest.mark.unit
    def test_multiple_subscriptions_returns_most_recent(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that with multiple subscriptions, most recent is returned."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_multi_123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create older Plus subscription
        older_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_old",
            stripe_customer_id="cus_multi_123",
            status="active",
            tier="plus",
            price_id="price_plus",
            created_at=datetime(2023, 1, 1),
        )
        test_db.add(older_sub)

        # Create newer Pro subscription
        newer_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_new",
            stripe_customer_id="cus_multi_123",
            status="active",
            tier="pro",
            price_id="price_pro",
            created_at=datetime(2024, 1, 1),
        )
        test_db.add(newer_sub)
        test_db.commit()

        tier = get_user_subscription_tier(test_user.id, test_db)
        assert tier == "pro"

    @pytest.mark.unit
    def test_inactive_subscription_returns_free(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that inactive subscription returns free tier."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_inactive_123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create inactive subscription
        inactive_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_inactive",
            stripe_customer_id="cus_inactive_123",
            status="inactive",
            tier="plus",
            price_id="price_plus",
        )
        test_db.add(inactive_sub)
        test_db.commit()

        tier = get_user_subscription_tier(test_user.id, test_db)
        assert tier == "free"

    @pytest.mark.unit
    def test_canceled_subscription_returns_free(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that canceled subscription returns free tier."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_canceled_123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create canceled subscription
        canceled_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_canceled",
            stripe_customer_id="cus_canceled_123",
            status="canceled",
            tier="pro",
            price_id="price_pro",
        )
        test_db.add(canceled_sub)
        test_db.commit()

        tier = get_user_subscription_tier(test_user.id, test_db)
        assert tier == "free"


class TestGetUserActiveSubscriptionCount:
    """Tests for get_user_active_subscription_count function."""

    @pytest.mark.unit
    def test_no_subscriptions_returns_zero(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that user with no subscriptions returns 0."""
        count = get_user_active_subscription_count(test_user.id, test_db)
        assert count == 0

    @pytest.mark.unit
    def test_single_subscription_returns_one(
        self,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
    ):
        """Test that user with one subscription returns 1."""
        count = get_user_active_subscription_count(test_user.id, test_db)
        assert count == 1

    @pytest.mark.unit
    def test_multiple_active_subscriptions(
        self,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college,
    ):
        """Test counting multiple active subscriptions."""
        # Create 3 active subscriptions
        for i in range(3):
            sub = Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=True,
                notification_count=0,
            )
            test_db.add(sub)
        test_db.commit()

        count = get_user_active_subscription_count(test_user.id, test_db)
        assert count == 3

    @pytest.mark.unit
    def test_ignores_inactive_subscriptions(
        self,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college,
    ):
        """Test that inactive subscriptions are not counted."""
        # Create 2 active and 2 inactive subscriptions
        for i in range(2):
            active_sub = Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=True,
                notification_count=0,
            )
            test_db.add(active_sub)

            inactive_sub = Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=False,
                notification_count=0,
            )
            test_db.add(inactive_sub)
        test_db.commit()

        count = get_user_active_subscription_count(test_user.id, test_db)
        assert count == 2


class TestGetSubscriptionFeatures:
    """Tests for get_subscription_features function."""

    @pytest.mark.unit
    def test_free_tier_features(self):
        """Test free tier feature set."""
        features = get_subscription_features("free")

        assert features["max_subscriptions"] == 3
        assert features["has_enrollment_analysis"] is False
        assert features["has_course_summary"] is False
        assert features["has_priority_notifications"] is False

    @pytest.mark.unit
    def test_plus_tier_features(self):
        """Test plus tier feature set."""
        features = get_subscription_features("plus")

        assert features["max_subscriptions"] == 10
        assert features["has_enrollment_analysis"] is True
        assert features["has_course_summary"] is True
        assert features["has_priority_notifications"] is False

    @pytest.mark.unit
    def test_pro_tier_features(self):
        """Test pro tier feature set."""
        features = get_subscription_features("pro")

        assert features["max_subscriptions"] == 50
        assert features["has_enrollment_analysis"] is True
        assert features["has_course_summary"] is True
        assert features["has_priority_notifications"] is True

    @pytest.mark.unit
    def test_invalid_tier_defaults_to_free(self):
        """Test that invalid tier defaults to free features."""
        features = get_subscription_features("invalid_tier")  # type: ignore

        # Should return free tier features as default
        assert features["max_subscriptions"] == 3
        assert features["has_enrollment_analysis"] is False


class TestRequirePremiumAccess:
    """Tests for require_premium_access function."""

    @pytest.mark.unit
    def test_free_user_raises_403(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that free tier user raises 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_premium_access(test_user.id, test_db)

        assert exc_info.value.status_code == 403
        assert "Premium subscription required" in exc_info.value.detail

    @pytest.mark.unit
    def test_plus_user_succeeds(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that Plus tier user passes check."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_premium_plus",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create active Plus subscription
        plus_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_plus",
            stripe_customer_id="cus_premium_plus",
            status="active",
            tier="plus",
            price_id="price_plus",
        )
        test_db.add(plus_sub)
        test_db.commit()

        # Should not raise
        require_premium_access(test_user.id, test_db)

    @pytest.mark.unit
    def test_pro_user_succeeds(
        self,
        test_db: Session,
        test_user: Profile,
    ):
        """Test that Pro tier user passes check."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_premium_pro",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create active Pro subscription
        pro_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_pro",
            stripe_customer_id="cus_premium_pro",
            status="active",
            tier="pro",
            price_id="price_pro",
        )
        test_db.add(pro_sub)
        test_db.commit()

        # Should not raise
        require_premium_access(test_user.id, test_db)


class TestCheckSubscriptionLimit:
    """Tests for check_subscription_limit function."""

    @pytest.mark.unit
    def test_free_user_under_limit(
        self,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college,
    ):
        """Test free user with 2 subscriptions (under 3 limit)."""
        # Create 2 subscriptions
        for i in range(2):
            sub = Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=True,
                notification_count=0,
            )
            test_db.add(sub)
        test_db.commit()

        can_subscribe = check_subscription_limit(test_user.id, test_db)
        assert can_subscribe is True

    @pytest.mark.unit
    def test_free_user_at_limit(
        self,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college,
    ):
        """Test free user with 3 subscriptions (at limit)."""
        # Create 3 subscriptions
        for i in range(3):
            sub = Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=True,
                notification_count=0,
            )
            test_db.add(sub)
        test_db.commit()

        can_subscribe = check_subscription_limit(test_user.id, test_db)
        assert can_subscribe is False

    @pytest.mark.unit
    def test_plus_user_under_limit(
        self,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college,
    ):
        """Test Plus user with 9 subscriptions (under 10 limit)."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_limit_plus",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create Plus subscription
        plus_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_plus",
            stripe_customer_id="cus_limit_plus",
            status="active",
            tier="plus",
            price_id="price_plus",
        )
        test_db.add(plus_sub)

        # Create 9 subscriptions
        for i in range(9):
            sub = Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=True,
                notification_count=0,
            )
            test_db.add(sub)
        test_db.commit()

        can_subscribe = check_subscription_limit(test_user.id, test_db)
        assert can_subscribe is True

    @pytest.mark.unit
    def test_pro_user_under_limit(
        self,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college,
    ):
        """Test Pro user with 49 subscriptions (under 50 limit)."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_limit_pro",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        # Create Pro subscription
        pro_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_pro",
            stripe_customer_id="cus_limit_pro",
            status="active",
            tier="pro",
            price_id="price_pro",
        )
        test_db.add(pro_sub)

        # Create 49 subscriptions
        for i in range(49):
            sub = Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=True,
                notification_count=0,
            )
            test_db.add(sub)
        test_db.commit()

        can_subscribe = check_subscription_limit(test_user.id, test_db)
        assert can_subscribe is True
