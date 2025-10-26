"""Tests for Stripe payment integration API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch
from sqlalchemy import select

from models.user import Profile
from models.stripe_customer import StripeCustomer
from models.stripe_subscription import StripeSubscription


class TestCreateCheckoutSession:
    """Tests for POST /api/stripe/create-checkout-session endpoint."""

    @pytest.mark.unit
    async def test_create_checkout_session_new_customer(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        mock_stripe,
    ):
        """Test creating checkout session for new customer."""
        with patch("api.routes.stripe.create_stripe_customer") as mock_create, patch(
            "api.routes.stripe.create_checkout_session"
        ) as mock_checkout, patch(
            "api.routes.stripe.get_price_id_for_tier"
        ) as mock_price:

            # Mock Stripe customer creation
            mock_customer = MagicMock()
            mock_customer.id = "cus_test123"
            mock_create.return_value = mock_customer

            # Mock checkout session creation
            mock_session = MagicMock()
            mock_session.id = "cs_test123"
            mock_session.url = "https://checkout.stripe.com/test"
            mock_checkout.return_value = mock_session

            # Mock price ID
            mock_price.return_value = "price_test123"

            response = await authenticated_client.post(
                "/api/stripe/create-checkout-session",
                json={"tier": "plus"},
            )

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["success"] is True
            data = response_json["data"]
            assert data["sessionId"] == "cs_test123"
            assert data["sessionUrl"] == "https://checkout.stripe.com/test"

            # Verify customer was created in database
            result = test_db.execute(
                select(StripeCustomer).where(StripeCustomer.user_id == test_user.id)
            )
            customer = result.scalar_one_or_none()
            assert customer is not None
            assert customer.stripe_customer_id == "cus_test123"

    @pytest.mark.unit
    async def test_create_checkout_session_existing_customer(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test creating checkout session for existing customer."""
        # Create existing Stripe customer
        existing_customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_existing123",
            email=test_user.email,
        )
        test_db.add(existing_customer)
        test_db.commit()

        with patch("api.routes.stripe.create_checkout_session") as mock_checkout, patch(
            "api.routes.stripe.get_price_id_for_tier"
        ) as mock_price:

            # Mock checkout session
            mock_session = MagicMock()
            mock_session.id = "cs_test123"
            mock_session.url = "https://checkout.stripe.com/test"
            mock_checkout.return_value = mock_session

            mock_price.return_value = "price_test123"

            response = await authenticated_client.post(
                "/api/stripe/create-checkout-session",
                json={"tier": "pro"},
            )

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["success"] is True

    @pytest.mark.unit
    async def test_create_checkout_session_invalid_tier(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test creating checkout session with invalid tier."""
        response = await authenticated_client.post(
            "/api/stripe/create-checkout-session",
            json={"tier": "invalid"},
        )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.unit
    async def test_create_checkout_session_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test creating checkout session without authentication."""
        response = await client.post(
            "/api/stripe/create-checkout-session",
            json={"tier": "plus"},
        )

        assert response.status_code == 401


class TestCreatePortalSession:
    """Tests for POST /api/stripe/create-portal-session endpoint."""

    @pytest.mark.unit
    async def test_create_portal_session_success(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test creating portal session successfully."""
        # Create Stripe customer
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        with patch("api.routes.stripe.create_portal_session") as mock_portal:
            # Mock portal session
            mock_session = MagicMock()
            mock_session.url = "https://billing.stripe.com/test"
            mock_portal.return_value = mock_session

            response = await authenticated_client.post(
                "/api/stripe/create-portal-session"
            )

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["success"] is True
            data = response_json["data"]
            assert data["sessionUrl"] == "https://billing.stripe.com/test"

    @pytest.mark.unit
    async def test_create_portal_session_no_customer(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test creating portal session without existing customer."""
        response = await authenticated_client.post("/api/stripe/create-portal-session")

        assert response.status_code == 404
        assert "No Stripe customer found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_create_portal_session_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test creating portal session without authentication."""
        response = await client.post("/api/stripe/create-portal-session")

        assert response.status_code == 401


class TestStripeWebhooks:
    """Tests for POST /api/stripe/webhooks endpoint."""

    @pytest.mark.unit
    async def test_webhook_customer_created(
        self,
        client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test handling customer.created webhook."""
        with patch("api.routes.stripe.verify_webhook_signature") as mock_verify:
            # Mock webhook event
            mock_event = MagicMock()
            mock_event.type = "customer.created"
            mock_customer = MagicMock()
            mock_customer.id = "cus_webhook123"
            mock_customer.get = lambda key: test_user.email if key == "email" else None
            mock_event.data.object = mock_customer
            mock_verify.return_value = mock_event

            response = await client.post(
                "/api/stripe/webhooks",
                content=b'{"type": "customer.created"}',
                headers={"stripe-signature": "test_signature"},
            )

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["success"] is True
            assert response_json["received"] is True

    @pytest.mark.unit
    async def test_webhook_subscription_created(
        self,
        client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test handling customer.subscription.created webhook."""
        # Create customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()

        with patch("api.routes.stripe.verify_webhook_signature") as mock_verify, patch(
            "api.routes.stripe.get_tier_from_price_id"
        ) as mock_tier:

            # Mock webhook event
            mock_event = MagicMock()
            mock_event.type = "customer.subscription.created"
            mock_subscription = MagicMock()
            mock_subscription.id = "sub_test123"
            mock_subscription.get = lambda key: (
                "cus_test123" if key == "customer" else None
            )
            mock_subscription.__getitem__ = lambda self, key: {
                "status": "active",
                "items": {"data": [{"price": {"id": "price_test123"}}]},
            }[key]
            mock_event.data.object = mock_subscription
            mock_verify.return_value = mock_event
            mock_tier.return_value = "plus"

            response = await client.post(
                "/api/stripe/webhooks",
                content=b'{"type": "customer.subscription.created"}',
                headers={"stripe-signature": "test_signature"},
            )

            assert response.status_code == 200

            # Verify subscription was created
            result = test_db.execute(
                select(StripeSubscription).where(
                    StripeSubscription.stripe_subscription_id == "sub_test123"
                )
            )
            subscription = result.scalar_one_or_none()
            assert subscription is not None
            assert subscription.tier == "plus"

    @pytest.mark.unit
    async def test_webhook_subscription_updated(
        self,
        client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test handling customer.subscription.updated webhook."""
        # Create customer
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            email=test_user.email,
        )
        test_db.add(customer)

        # Create existing subscription
        subscription = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            status="active",
            price_id="price_old",
            tier="plus",
        )
        test_db.add(subscription)
        test_db.commit()

        with patch("api.routes.stripe.verify_webhook_signature") as mock_verify, patch(
            "api.routes.stripe.get_tier_from_price_id"
        ) as mock_tier:

            mock_event = MagicMock()
            mock_event.type = "customer.subscription.updated"
            mock_subscription = MagicMock()
            mock_subscription.id = "sub_test123"
            mock_subscription.get = lambda key: (
                "cus_test123" if key == "customer" else None
            )
            mock_subscription.__getitem__ = lambda self, key: {
                "status": "active",
                "items": {"data": [{"price": {"id": "price_new"}}]},
            }[key]
            mock_event.data.object = mock_subscription
            mock_verify.return_value = mock_event
            mock_tier.return_value = "pro"

            response = await client.post(
                "/api/stripe/webhooks",
                content=b'{"type": "customer.subscription.updated"}',
                headers={"stripe-signature": "test_signature"},
            )

            assert response.status_code == 200

            # Verify subscription was updated
            test_db.refresh(subscription)
            assert subscription.tier == "pro"
            assert subscription.price_id == "price_new"

    @pytest.mark.unit
    async def test_webhook_subscription_deleted(
        self,
        client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test handling customer.subscription.deleted webhook."""
        # Create customer and subscription
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            email=test_user.email,
        )
        test_db.add(customer)

        subscription = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            status="active",
            price_id="price_test",
            tier="plus",
        )
        test_db.add(subscription)
        test_db.commit()

        with patch("api.routes.stripe.verify_webhook_signature") as mock_verify:
            mock_event = MagicMock()
            mock_event.type = "customer.subscription.deleted"
            mock_subscription = MagicMock()
            mock_subscription.id = "sub_test123"
            mock_event.data.object = mock_subscription
            mock_verify.return_value = mock_event

            response = await client.post(
                "/api/stripe/webhooks",
                content=b'{"type": "customer.subscription.deleted"}',
                headers={"stripe-signature": "test_signature"},
            )

            assert response.status_code == 200

            # Verify subscription was canceled
            test_db.refresh(subscription)
            assert subscription.status == "canceled"

    @pytest.mark.unit
    async def test_webhook_no_signature(
        self,
        client: AsyncClient,
    ):
        """Test webhook without signature header."""
        response = await client.post(
            "/api/stripe/webhooks",
            content=b'{"type": "customer.created"}',
        )

        assert response.status_code == 400

    @pytest.mark.unit
    async def test_webhook_invalid_signature(
        self,
        client: AsyncClient,
    ):
        """Test webhook with invalid signature."""
        with patch("api.routes.stripe.verify_webhook_signature") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid signature")

            response = await client.post(
                "/api/stripe/webhooks",
                content=b'{"type": "customer.created"}',
                headers={"stripe-signature": "invalid_signature"},
            )

            assert response.status_code == 400
