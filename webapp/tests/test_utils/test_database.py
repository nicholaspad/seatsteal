"""Tests for database utility functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from utils.database import get_stripe_customer
from models.user import Profile
from models.stripe_customer import StripeCustomer


class TestGetStripeCustomer:
    """Tests for get_stripe_customer utility function."""

    @pytest.mark.unit
    async def test_get_existing_customer(self, test_db: Session, test_user: Profile):
        """Test retrieving an existing Stripe customer."""
        # Create existing customer
        existing_customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            email=test_user.email,
        )
        test_db.add(existing_customer)
        test_db.commit()

        # Get customer should return existing one
        result = await get_stripe_customer(test_user.id, test_db)

        assert result is not None
        assert result.user_id == test_user.id
        assert result.stripe_customer_id == "cus_test123"
        assert result.email == test_user.email

    @pytest.mark.unit
    async def test_create_new_customer(self, test_db: Session, test_user: Profile):
        """Test creating a new Stripe customer when none exists."""
        # Mock Stripe API
        mock_stripe_customer = MagicMock()
        mock_stripe_customer.id = "cus_new123"

        with patch(
            "utils.database.create_stripe_customer", new_callable=AsyncMock
        ) as mock_create, patch("utils.database.invalidate_user_caches") as mock_cache:
            mock_create.return_value = mock_stripe_customer

            # Get customer should create new one
            result = await get_stripe_customer(test_user.id, test_db)

            assert result is not None
            assert result.user_id == test_user.id
            assert result.stripe_customer_id == "cus_new123"
            assert result.email == test_user.email

            # Verify Stripe API was called
            mock_create.assert_called_once_with(test_user.email, str(test_user.id))

            # Verify cache was invalidated
            mock_cache.assert_called_once_with(str(test_user.id))

            # Verify customer was saved to database
            saved_customer = (
                test_db.query(StripeCustomer)
                .filter(StripeCustomer.user_id == test_user.id)
                .first()
            )
            assert saved_customer is not None
            assert saved_customer.stripe_customer_id == "cus_new123"

    @pytest.mark.unit
    async def test_user_not_found(self, test_db: Session):
        """Test behavior when user doesn't exist."""
        non_existent_user_id = uuid4()

        result = await get_stripe_customer(non_existent_user_id, test_db)

        assert result is None

    @pytest.mark.unit
    async def test_stripe_api_failure(self, test_db: Session, test_user: Profile):
        """Test handling of Stripe API failures."""
        with patch(
            "utils.database.create_stripe_customer", new_callable=AsyncMock
        ) as mock_create:
            # Simulate Stripe API failure
            mock_create.side_effect = Exception("Stripe API error")

            result = await get_stripe_customer(test_user.id, test_db)

            assert result is None

            # Verify no customer was created in database
            saved_customer = (
                test_db.query(StripeCustomer)
                .filter(StripeCustomer.user_id == test_user.id)
                .first()
            )
            assert saved_customer is None

    @pytest.mark.unit
    async def test_idempotency(self, test_db: Session, test_user: Profile):
        """Test that calling get_stripe_customer multiple times is safe."""
        mock_stripe_customer = MagicMock()
        mock_stripe_customer.id = "cus_idempotent123"

        with patch(
            "utils.database.create_stripe_customer", new_callable=AsyncMock
        ) as mock_create, patch("utils.database.invalidate_user_caches"):
            mock_create.return_value = mock_stripe_customer

            # First call - creates customer
            result1 = await get_stripe_customer(test_user.id, test_db)
            assert result1 is not None
            assert result1.stripe_customer_id == "cus_idempotent123"

            # Second call - should return existing customer without API call
            result2 = await get_stripe_customer(test_user.id, test_db)
            assert result2 is not None
            assert result2.stripe_customer_id == "cus_idempotent123"
            assert result2.id == result1.id

            # Stripe API should only be called once
            assert mock_create.call_count == 1

    @pytest.mark.unit
    async def test_database_commit_failure(self, test_db: Session, test_user: Profile):
        """Test handling of database commit failures."""
        mock_stripe_customer = MagicMock()
        mock_stripe_customer.id = "cus_commit_fail123"

        with patch(
            "utils.database.create_stripe_customer", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_stripe_customer

            # Mock db.commit to raise an exception
            original_commit = test_db.commit
            test_db.commit = MagicMock(side_effect=Exception("Database error"))

            try:
                result = await get_stripe_customer(test_user.id, test_db)

                # Should return None on database error
                assert result is None
            finally:
                # Restore original commit method
                test_db.commit = original_commit
