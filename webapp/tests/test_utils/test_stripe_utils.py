"""Tests for Stripe utility functions."""

import pytest
import stripe
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from utils.stripe_utils import (
    get_price_id_for_tier,
    get_tier_from_price_id,
    verify_webhook_signature,
    extend_subscription_trial,
)


class TestGetPriceIdForTier:
    """Tests for get_price_id_for_tier function."""

    @pytest.mark.unit
    def test_plus_tier_returns_correct_price_id(self):
        """Test that Plus tier returns the correct Stripe price ID."""
        with patch("utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"

            price_id = get_price_id_for_tier("plus")
            assert price_id == "price_plus_123"

    @pytest.mark.unit
    def test_pro_tier_returns_correct_price_id(self):
        """Test that Pro tier returns the correct Stripe price ID."""
        with patch("utils.stripe_utils.settings") as mock_settings:
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
        with patch("utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            tier = get_tier_from_price_id("price_plus_123")
            assert tier == "plus"

    @pytest.mark.unit
    def test_pro_price_id_returns_pro(self):
        """Test that Pro price ID returns pro tier."""
        with patch("utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            tier = get_tier_from_price_id("price_pro_456")
            assert tier == "pro"

    @pytest.mark.unit
    def test_unknown_price_id_returns_none(self):
        """Test that unknown price ID returns None."""
        with patch("utils.stripe_utils.settings") as mock_settings:
            mock_settings.STRIPE_PLUS_PRICE_ID = "price_plus_123"
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_456"

            tier = get_tier_from_price_id("price_unknown_789")
            assert tier is None

    @pytest.mark.unit
    def test_empty_price_id_returns_none(self):
        """Test that empty price ID returns None."""
        with patch("utils.stripe_utils.settings") as mock_settings:
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


class TestExtendSubscriptionTrial:
    """Tests for extend_subscription_trial."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_expired_trial_end_starts_from_now(self):
        expired = datetime.now(timezone.utc) - timedelta(days=30)
        mock_sub = MagicMock()
        mock_sub.trial_end = int(expired.timestamp())

        with patch(
            "utils.stripe_utils.stripe.Subscription.retrieve"
        ) as mock_retrieve, patch(
            "utils.stripe_utils.stripe.Subscription.modify"
        ) as mock_modify:
            mock_retrieve.return_value = mock_sub
            mock_modify.return_value = mock_sub

            before = datetime.now(timezone.utc)
            await extend_subscription_trial("sub_expired_123", additional_days=7)
            after = datetime.now(timezone.utc)

            kwargs = mock_modify.call_args.kwargs
            new_ts = kwargs["trial_end"]
            new_end = datetime.fromtimestamp(new_ts, tz=timezone.utc)
            # Stripe would reject expired+7d (still in the past). The extra
            # week must start from now. Unix timestamps drop microseconds.
            assert new_end >= before + timedelta(days=7) - timedelta(seconds=1)
            assert new_end <= after + timedelta(days=7)
            assert new_end > expired + timedelta(days=8)
            assert kwargs["proration_behavior"] == "none"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_future_trial_end_adds_days_to_existing_end(self):
        future = datetime.now(timezone.utc) + timedelta(days=4)
        mock_sub = MagicMock()
        mock_sub.trial_end = int(future.timestamp())

        with patch(
            "utils.stripe_utils.stripe.Subscription.retrieve"
        ) as mock_retrieve, patch(
            "utils.stripe_utils.stripe.Subscription.modify"
        ) as mock_modify:
            mock_retrieve.return_value = mock_sub
            mock_modify.return_value = mock_sub

            await extend_subscription_trial("sub_active_123", additional_days=7)

            kwargs = mock_modify.call_args.kwargs
            new_ts = kwargs["trial_end"]
            new_end = datetime.fromtimestamp(new_ts, tz=timezone.utc)
            expected = future + timedelta(days=7)
            assert abs((new_end - expected).total_seconds()) < 2
            assert kwargs["proration_behavior"] == "none"
