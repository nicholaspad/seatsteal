"""Stripe integration utilities"""

import stripe
from typing import Literal, Optional
from ..config import settings

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

StripePriceTier = Literal["plus", "pro"]


def get_price_id_for_tier(tier: StripePriceTier) -> str:
    """Get Stripe price ID for a subscription tier"""
    if tier == "plus":
        return settings.STRIPE_PLUS_PRICE_ID
    elif tier == "pro":
        return settings.STRIPE_PRO_PRICE_ID
    else:
        raise ValueError(f"Invalid tier: {tier}")


def get_tier_from_price_id(price_id: str) -> Optional[StripePriceTier]:
    """Get subscription tier from Stripe price ID"""
    if price_id == settings.STRIPE_PLUS_PRICE_ID:
        return "plus"
    elif price_id == settings.STRIPE_PRO_PRICE_ID:
        return "pro"
    return None


async def create_stripe_customer(email: str, user_id: str) -> stripe.Customer:
    """Create a new Stripe customer"""
    return stripe.Customer.create(
        email=email,
        metadata={"user_id": user_id},
    )


async def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    user_id: str,
) -> stripe.checkout.Session:
    """Create a Stripe checkout session for subscription"""
    return stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user_id},
    )


async def create_portal_session(
    customer_id: str, return_url: str
) -> stripe.billing_portal.Session:
    """Create a Stripe billing portal session"""
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )


def verify_webhook_signature(payload: str, sig_header: str) -> stripe.Event:
    """Verify Stripe webhook signature and construct event"""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        # Invalid payload
        raise ValueError(f"Invalid payload: {str(e)}")
    except stripe.SignatureVerificationError as e:
        # Invalid signature
        raise ValueError(f"Invalid signature: {str(e)}")
