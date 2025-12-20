"""Stripe integration utilities"""

import stripe
import logging
from typing import Literal, Optional
from config import settings

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Validate Stripe configuration at startup
if not settings.STRIPE_SECRET_KEY:
    logger.warning(
        "STRIPE_SECRET_KEY is not configured. Stripe payments will not work."
    )
else:
    logger.info(
        f"Stripe initialized with key starting with: {settings.STRIPE_SECRET_KEY[:12]}..."
    )

if not settings.STRIPE_PLUS_PRICE_ID:
    logger.warning(
        "STRIPE_PLUS_PRICE_ID is not configured. Plus tier monthly subscriptions will fail."
    )

if not settings.STRIPE_PRO_PRICE_ID:
    logger.warning(
        "STRIPE_PRO_PRICE_ID is not configured. Pro tier monthly subscriptions will fail."
    )

StripePriceTier = Literal["plus", "pro"]
StripeBillingInterval = Literal["monthly", "annual"]


def get_price_id_for_tier(
    tier: StripePriceTier, interval: StripeBillingInterval = "monthly"
) -> str:
    """Get Stripe price ID for a subscription tier and billing interval"""
    if tier == "plus":
        if interval == "annual" and settings.STRIPE_PLUS_ANNUAL_PRICE_ID:
            return settings.STRIPE_PLUS_ANNUAL_PRICE_ID
        return settings.STRIPE_PLUS_PRICE_ID
    elif tier == "pro":
        if interval == "annual" and settings.STRIPE_PRO_ANNUAL_PRICE_ID:
            return settings.STRIPE_PRO_ANNUAL_PRICE_ID
        return settings.STRIPE_PRO_PRICE_ID
    else:
        raise ValueError(f"Invalid tier: {tier}")


def get_tier_from_price_id(price_id: str) -> Optional[StripePriceTier]:
    """Get subscription tier from Stripe price ID (works for both monthly and annual)"""
    if price_id in (
        settings.STRIPE_PLUS_PRICE_ID,
        settings.STRIPE_PLUS_ANNUAL_PRICE_ID,
    ):
        return "plus"
    elif price_id in (
        settings.STRIPE_PRO_PRICE_ID,
        settings.STRIPE_PRO_ANNUAL_PRICE_ID,
    ):
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


def verify_webhook_signature(payload: bytes, sig_header: str) -> stripe.Event:
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


async def create_trial_subscription(
    customer_id: str,
    tier: StripePriceTier,
    trial_days: int = 7,
    user_id: str,
    metadata: dict = None,
) -> stripe.Subscription:
    """Create a subscription with trial period that auto-cancels without payment

    Args:
        customer_id: Stripe customer ID
        tier: Subscription tier (plus or pro)
        trial_days: Number of days for trial (default 7)
        user_id: User ID for metadata
        metadata: Additional metadata to attach

    Returns:
        Stripe Subscription object
    """
    price_id = get_price_id_for_tier(tier, "monthly")

    subscription_metadata = {"user_id": user_id, "source": "referral_trial"}
    if metadata:
        subscription_metadata.update(metadata)

    return stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        trial_period_days=trial_days,
        trial_settings={"end_behavior": {"missing_payment_method": "cancel"}},
        metadata=subscription_metadata,
    )


async def extend_subscription_trial(
    subscription_id: str,
    additional_days: int = 7,
) -> stripe.Subscription:
    """Extend an existing subscription's trial by additional days

    Args:
        subscription_id: Stripe subscription ID
        additional_days: Number of days to add (default 7)

    Returns:
        Updated Stripe Subscription object
    """
    import datetime

    subscription = stripe.Subscription.retrieve(subscription_id)

    # Calculate new trial_end (current trial + additional days)
    if subscription.trial_end:
        current_trial = datetime.datetime.fromtimestamp(subscription.trial_end)
    else:
        current_trial = datetime.datetime.now()

    new_trial_end = current_trial + datetime.timedelta(days=additional_days)

    return stripe.Subscription.modify(
        subscription_id,
        trial_end=int(new_trial_end.timestamp()),
    )
