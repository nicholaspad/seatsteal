"""Tests for Stripe utility functions."""

import pytest
import stripe
from unittest.mock import patch, MagicMock

from webapp.utils.stripe_utils import (
    get_price_id_for_tier,
    get_tier_from_price_id,
    verify_webhook_signature,
)


class TestGetPriceIdForTier:
    """Tests for get_price_id_for_tier function."""

    @pytest.mark.unit
    def test_plus_tier_returns_correct_price_id(self):
        """Test that Plus tier returns the correct Stripe price ID."""
        with patch("webapp.utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"

            price_id = get_price_id_for_tier("plus")
            assert price_id == "price_plus_123"

    @pytest.mark.unit
    def test_pro_tier_returns_correct_price_id(self):
        """Test that Pro tier returns the correct Stripe price ID."""
        with patch("webapp.utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            price_id = get_price_id_for_tier("pro")
            assert price_id == "price_pro_456"

    @pytest.mark.unit
    def test_invalid_tier_raises_value_error(self):
        """Test that invalid tier raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_price_id_for_tier("invalid")  # type: ignore

        assert "Invalid tier" in str(exc_info.value)


class TestGetTierFromPriceId:
    """Tests for get_tier_from_price_id function."""

    @pytest.mark.unit
    def test_plus_price_id_returns_plus(self):
        """Test that Plus price ID returns plus tier."""
        with patch("webapp.utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            tier = get_tier_from_price_id("price_plus_123")
            assert tier == "plus"

    @pytest.mark.unit
    def test_pro_price_id_returns_pro(self):
        """Test that Pro price ID returns pro tier."""
        with patch("webapp.utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            tier = get_tier_from_price_id("price_pro_456")
            assert tier == "pro"

    @pytest.mark.unit
    def test_unknown_price_id_returns_none(self):
        """Test that unknown price ID returns None."""
        with patch("webapp.utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            tier = get_tier_from_price_id("price_unknown_789")
            assert tier is None

    @pytest.mark.unit
    def test_empty_price_id_returns_none(self):
        """Test that empty price ID returns None."""
        with patch("webapp.utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            tier = get_tier_from_price_id("")
            assert tier is None


class TestVerifyWebhookSignature:
    """Tests for verify_webhook_signature function."""

    @pytest.mark.unit
    def test_valid_signature_returns_event(self):
        """Test that valid signature returns Stripe event."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            # Mock successful event construction
            mock_event = MagicMock()
            mock_event.type = "customer.created"
            mock_construct.return_value = mock_event

            payload = '{"type": "customer.created"}'
            sig_header = "t=1234567890,v1=signature_hash"

            event = verify_webhook_signature(payload, sig_header)

            assert event == mock_event
            assert event.type == "customer.created"
            mock_construct.assert_called_once()

    @pytest.mark.unit
    def test_invalid_payload_raises_value_error(self):
        """Test that invalid JSON payload raises ValueError."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            # Mock ValueError for invalid payload
            mock_construct.side_effect = ValueError("Invalid JSON")

            payload = "not valid json"
            sig_header = "t=1234567890,v1=signature_hash"

            with pytest.raises(ValueError) as exc_info:
                verify_webhook_signature(payload, sig_header)

            assert "Invalid payload" in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_signature_raises_value_error(self):
        """Test that invalid signature raises ValueError."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            # Mock SignatureVerificationError
            mock_construct.side_effect = stripe.SignatureVerificationError(
                "Signature mismatch", sig_header="bad_signature"
            )

            payload = '{"type": "customer.created"}'
            sig_header = "invalid_signature"

            with pytest.raises(ValueError) as exc_info:
                verify_webhook_signature(payload, sig_header)

            assert "Invalid signature" in str(exc_info.value)

    @pytest.mark.unit
    def test_missing_signature_raises_error(self):
        """Test that missing signature raises error."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            # Mock error for missing signature
            mock_construct.side_effect = stripe.SignatureVerificationError(
                "No signatures found", sig_header=None
            )

            payload = '{"type": "customer.created"}'
            sig_header = ""

            with pytest.raises(ValueError) as exc_info:
                verify_webhook_signature(payload, sig_header)

            assert "Invalid signature" in str(exc_info.value)


class TestAsyncStripeUtilFunctions:
    """Optional tests for async Stripe utility functions.

    These are already well-covered by route integration tests,
    but included here for completeness.
    """

    @pytest.mark.unit
    async def test_create_stripe_customer(self):
        """Test creating a Stripe customer."""
        from webapp.utils.stripe_utils import create_stripe_customer

        with patch("stripe.Customer.create") as mock_create:
            mock_customer = MagicMock()
            mock_customer.id = "cus_test123"
            mock_create.return_value = mock_customer

            customer = await create_stripe_customer("test@example.com", "user_123")

            assert customer.id == "cus_test123"
            mock_create.assert_called_once_with(
                email="test@example.com",
                metadata={"user_id": "user_123"},
            )

    @pytest.mark.unit
    async def test_create_checkout_session(self):
        """Test creating a Stripe checkout session."""
        from webapp.utils.stripe_utils import create_checkout_session

        with patch("stripe.checkout.Session.create") as mock_create:
            mock_session = MagicMock()
            mock_session.id = "cs_test123"
            mock_session.url = "https://checkout.stripe.com/test"
            mock_create.return_value = mock_session

            session = await create_checkout_session(
                customer_id="cus_123",
                price_id="price_123",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
                user_id="user_123",
            )

            assert session.id == "cs_test123"
            assert session.url == "https://checkout.stripe.com/test"
            mock_create.assert_called_once()

    @pytest.mark.unit
    async def test_create_portal_session(self):
        """Test creating a Stripe billing portal session."""
        from webapp.utils.stripe_utils import create_portal_session

        with patch("stripe.billing_portal.Session.create") as mock_create:
            mock_session = MagicMock()
            mock_session.url = "https://billing.stripe.com/test"
            mock_create.return_value = mock_session

            session = await create_portal_session(
                customer_id="cus_123",
                return_url="https://example.com/account",
            )

            assert session.url == "https://billing.stripe.com/test"
            mock_create.assert_called_once_with(
                customer="cus_123",
                return_url="https://example.com/account",
            )
