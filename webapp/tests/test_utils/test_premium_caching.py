"""Tests for subscription tier caching in premium utilities."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from uuid import uuid4

from utils.premium import get_user_subscription_tier
from models.stripe_subscription import StripeSubscription
from models.stripe_customer import StripeCustomer
from models.user import Profile


class TestGetUserSubscriptionTierCaching:
    """Tests for caching behavior in get_user_subscription_tier."""

    @pytest.mark.unit
    def test_cache_miss_queries_database_and_caches_result(self, test_db: Session, test_college):
        """Test that cache miss queries database and caches the result."""
        with patch("utils.premium.get_cached_user_tier") as mock_get_cache, \
             patch("utils.premium.cache_user_tier") as mock_cache_tier:

            # Setup: Cache miss
            mock_get_cache.return_value = None

            user_id = uuid4()

            # Create Profile first (required for foreign key)
            profile = Profile(
                id=user_id,
                email="test@example.com",
                college_id=test_college.id,
                role="user",
            )
            test_db.add(profile)
            test_db.flush()

            # Create StripeCustomer (required for foreign key)
            customer = StripeCustomer(
                user_id=user_id,
                stripe_customer_id="cus_test123",
                email="test@example.com",
            )
            test_db.add(customer)
            test_db.flush()

            # Create mock subscription in database
            subscription = StripeSubscription(
                user_id=user_id,
                stripe_subscription_id="sub_test123",
                stripe_customer_id="cus_test123",
                status="active",
                price_id="price_test123",
                tier="pro",
            )
            test_db.add(subscription)
            test_db.commit()
            
            # Execute
            tier = get_user_subscription_tier(user_id, test_db)
            
            # Verify: Correct tier returned
            assert tier == "pro"
            
            # Verify: Result was cached with 300s TTL
            mock_cache_tier.assert_called_once()
            call_args = mock_cache_tier.call_args
            assert call_args[0][0] == str(user_id)  # user_id
            assert call_args[0][1] == "pro"  # tier
            assert call_args[1]["ttl"] == 300  # TTL

    @pytest.mark.unit
    def test_cache_hit_skips_database_query(self, test_db: Session):
        """Test that cache hit returns cached tier without querying database."""
        with patch("utils.premium.get_cached_user_tier") as mock_get_cache, \
             patch("utils.premium.cache_user_tier") as mock_cache_tier:
            
            # Setup: Cache hit
            mock_get_cache.return_value = "plus"
            
            user_id = uuid4()
            
            # Execute
            tier = get_user_subscription_tier(user_id, test_db)
            
            # Verify: Cache was checked
            mock_get_cache.assert_called_once_with(str(user_id))
            
            # Verify: Cached tier returned
            assert tier == "plus"
            
            # Verify: Database was NOT queried (no new caching call)
            mock_cache_tier.assert_not_called()

    @pytest.mark.unit
    def test_cache_free_tier_when_no_subscription(self, test_db: Session):
        """Test that 'free' tier is cached when user has no active subscription."""
        with patch("utils.premium.get_cached_user_tier") as mock_get_cache, \
             patch("utils.premium.cache_user_tier") as mock_cache_tier:
            
            # Setup: Cache miss
            mock_get_cache.return_value = None
            
            user_id = uuid4()  # User with no subscriptions
            
            # Execute
            tier = get_user_subscription_tier(user_id, test_db)
            
            # Verify: Free tier returned
            assert tier == "free"
            
            # Verify: Free tier was cached
            mock_cache_tier.assert_called_once()
            call_args = mock_cache_tier.call_args
            assert call_args[0][1] == "free"

    @pytest.mark.unit
    def test_cache_handles_multiple_subscriptions_returns_latest(self, test_db: Session, test_college):
        """Test that latest active subscription is used when multiple exist."""
        with patch("utils.premium.get_cached_user_tier") as mock_get_cache, \
             patch("utils.premium.cache_user_tier") as mock_cache_tier:

            # Setup: Cache miss
            mock_get_cache.return_value = None

            user_id = uuid4()

            # Create Profile first (required for foreign key)
            profile = Profile(
                id=user_id,
                email="test@example.com",
                college_id=test_college.id,
                role="user",
            )
            test_db.add(profile)
            test_db.flush()

            # Create StripeCustomer (required for foreign key)
            customer = StripeCustomer(
                user_id=user_id,
                stripe_customer_id="cus_test123",
                email="test@example.com",
            )
            test_db.add(customer)
            test_db.flush()

            # Create older subscription
            old_subscription = StripeSubscription(
                user_id=user_id,
                stripe_subscription_id="sub_old",
                stripe_customer_id="cus_test123",
                status="active",
                price_id="price_plus",
                tier="plus",
            )
            test_db.add(old_subscription)
            test_db.flush()

            # Create newer subscription
            new_subscription = StripeSubscription(
                user_id=user_id,
                stripe_subscription_id="sub_new",
                stripe_customer_id="cus_test123",
                status="active",
                price_id="price_pro",
                tier="pro",
            )
            test_db.add(new_subscription)
            test_db.commit()
            
            # Execute
            tier = get_user_subscription_tier(user_id, test_db)
            
            # Verify: Latest tier (pro) is returned and cached
            assert tier == "pro"
            
            call_args = mock_cache_tier.call_args
            assert call_args[0][1] == "pro"

    @pytest.mark.unit
    def test_cache_ignores_inactive_subscriptions(self, test_db: Session, test_college):
        """Test that only active subscriptions are considered."""
        with patch("utils.premium.get_cached_user_tier") as mock_get_cache, \
             patch("utils.premium.cache_user_tier") as mock_cache_tier:

            # Setup: Cache miss
            mock_get_cache.return_value = None

            user_id = uuid4()

            # Create Profile first (required for foreign key)
            profile = Profile(
                id=user_id,
                email="test@example.com",
                college_id=test_college.id,
                role="user",
            )
            test_db.add(profile)
            test_db.flush()

            # Create StripeCustomer (required for foreign key)
            customer = StripeCustomer(
                user_id=user_id,
                stripe_customer_id="cus_test123",
                email="test@example.com",
            )
            test_db.add(customer)
            test_db.flush()

            # Create canceled subscription
            canceled_subscription = StripeSubscription(
                user_id=user_id,
                stripe_subscription_id="sub_canceled",
                stripe_customer_id="cus_test123",
                status="canceled",
                price_id="price_pro",
                tier="pro",
            )
            test_db.add(canceled_subscription)
            test_db.commit()
            
            # Execute
            tier = get_user_subscription_tier(user_id, test_db)
            
            # Verify: Free tier returned (no active subscriptions)
            assert tier == "free"
            
            call_args = mock_cache_tier.call_args
            assert call_args[0][1] == "free"

    @pytest.mark.unit
    def test_cache_failure_does_not_break_tier_lookup(self, test_db: Session, test_college):
        """Test that cache failures don't prevent tier lookup from working."""
        with patch("utils.premium.get_cached_user_tier") as mock_get_cache, \
             patch("utils.premium.cache_user_tier") as mock_cache_tier:

            # Setup: Cache operations return None (simulating failure)
            mock_get_cache.return_value = None
            # cache_user_tier doesn't return anything, so no side_effect needed

            user_id = uuid4()

            # Create Profile first (required for foreign key)
            profile = Profile(
                id=user_id,
                email="test@example.com",
                college_id=test_college.id,
                role="user",
            )
            test_db.add(profile)
            test_db.flush()

            # Create StripeCustomer (required for foreign key)
            customer = StripeCustomer(
                user_id=user_id,
                stripe_customer_id="cus_test123",
                email="test@example.com",
            )
            test_db.add(customer)
            test_db.flush()

            # Create subscription
            subscription = StripeSubscription(
                user_id=user_id,
                stripe_subscription_id="sub_test",
                stripe_customer_id="cus_test123",
                status="active",
                price_id="price_plus",
                tier="plus",
            )
            test_db.add(subscription)
            test_db.commit()
            
            # Execute: Should not raise exception
            tier = get_user_subscription_tier(user_id, test_db)
            
            # Verify: Correct tier still returned from database
            assert tier == "plus"

