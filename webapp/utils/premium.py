"""Premium subscription utilities for handling user tiers and feature access"""

import logging
from typing import Any, Literal, Optional, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, case, desc
from uuid import UUID

from models.stripe_subscription import StripeSubscription
from models.subscription import Subscription
from utils.cache import get_cached_user_tier, cache_user_tier

logger = logging.getLogger(__name__)

# Subscription tier types
SubscriptionTier = Literal["free", "plus", "pro"]

# Stripe statuses that still count as a paid plan for tier lookup and
# notification cadence. past_due is included while Stripe is retrying;
# canceled / unpaid / incomplete_expired and anything else fall through
# to free.
PAID_STRIPE_STATUSES = ("active", "trialing", "past_due")


# Feature limits per tier
TIER_FEATURES = {
    "free": {
        "max_subscriptions": 1,
        "has_enrollment_analysis": False,
        "has_course_summary": False,
        "has_priority_notifications": False,
    },
    "plus": {
        "max_subscriptions": 5,
        "has_enrollment_analysis": False,
        "has_course_summary": False,
        "has_priority_notifications": False,
    },
    "pro": {
        "max_subscriptions": 20,
        "has_enrollment_analysis": True,
        "has_course_summary": True,
        "has_priority_notifications": True,
    },
}


def stripe_tier_rank(tier: Optional[str]) -> int:
    """Lower is better: pro (0) before plus (1) before anything else (2)."""
    if tier == "pro":
        return 0
    if tier == "plus":
        return 1
    return 2


def paid_stripe_plan_order():
    """Order paid Stripe rows: pro before plus, then newest, then highest id."""
    return (
        case(
            (StripeSubscription.tier == "pro", stripe_tier_rank("pro")),
            (StripeSubscription.tier == "plus", stripe_tier_rank("plus")),
            else_=stripe_tier_rank(None),
        ),
        desc(StripeSubscription.created_at),
        desc(StripeSubscription.id),
    )


def _stripe_object_tier(subscription: Any) -> Optional[str]:
    """Resolve plus/pro from a Stripe API object.

    On stripe>=13, ``subscription.items`` is dict.items, not the line items.
    Use the same bracket access as the webhook handler.
    """
    price_id = None
    try:
        price_id = subscription["items"]["data"][0]["price"]["id"]
    except Exception:
        logger.exception(
            "Failed to read price id from Stripe subscription %s",
            (
                subscription.get("id")
                if hasattr(subscription, "get")
                else getattr(subscription, "id", None)
            ),
        )

    if isinstance(price_id, str) and price_id:
        from utils.stripe_utils import get_tier_from_price_id

        return get_tier_from_price_id(price_id)

    tier = getattr(subscription, "tier", None)
    if isinstance(tier, str) and tier:
        return tier
    return None


def pick_highest_paid_stripe_subscription(subscriptions: Sequence[Any]) -> Any:
    """Same ranking as paid_stripe_plan_order, for Stripe API objects.

    pro before plus, then newest ``created``, then id.
    """

    def sort_key(sub: Any):
        created = getattr(sub, "created", None)
        if not isinstance(created, (int, float)):
            created = 0
        sub_id = str(getattr(sub, "id", "") or "")
        return (stripe_tier_rank(_stripe_object_tier(sub)), -int(created), sub_id)

    return min(subscriptions, key=sort_key)


def paid_stripe_plan_subquery():
    """One paid Stripe plan per user. Same ranking as get_user_subscription_tier."""
    return (
        select(
            StripeSubscription.user_id,
            StripeSubscription.tier,
        )
        .where(StripeSubscription.status.in_(PAID_STRIPE_STATUSES))
        .distinct(StripeSubscription.user_id)
        .order_by(
            StripeSubscription.user_id,
            *paid_stripe_plan_order(),
        )
        .subquery()
    )


def get_user_subscription_tier(user_id: UUID, db: Session) -> SubscriptionTier:
    """Get the subscription tier for a user based on their paid Stripe plan"""
    user_id_str = str(user_id)

    # Try to get tier from cache first (300s TTL)
    cached_tier = get_cached_user_tier(user_id_str)
    if cached_tier:
        return cached_tier  # type: ignore

    # Cache miss - query for the highest paid Stripe plan
    result = db.execute(
        select(StripeSubscription)
        .where(
            and_(
                StripeSubscription.user_id == user_id,
                StripeSubscription.status.in_(PAID_STRIPE_STATUSES),
            )
        )
        .order_by(*paid_stripe_plan_order())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        tier = "free"
    else:
        tier = subscription.tier  # type: ignore

    # Cache the tier for future requests (300s TTL)
    cache_user_tier(user_id_str, tier, ttl=300)

    return tier  # type: ignore


def get_user_active_subscription_count(user_id: UUID, db: Session) -> int:
    """Get count of active subscriptions for a user"""
    result = db.execute(
        select(func.count())
        .select_from(Subscription)
        .where(and_(Subscription.user_id == user_id, Subscription.is_active == True))
    )
    return result.scalar() or 0


def get_subscription_features(tier: SubscriptionTier) -> dict:
    """Get feature set for a subscription tier"""
    return TIER_FEATURES.get(tier, TIER_FEATURES["free"])


def require_premium_access(user_id: UUID, db: Session) -> None:
    """Raise exception if user doesn't have premium access (Plus or Pro)"""
    from fastapi import HTTPException, status

    tier = get_user_subscription_tier(user_id, db)
    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required (Plus or Pro)",
        )


def require_pro_access(user_id: UUID, db: Session) -> None:
    """Raise exception if user doesn't have Pro access"""
    from fastapi import HTTPException, status

    tier = get_user_subscription_tier(user_id, db)
    if tier != "pro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro subscription required",
        )


def check_subscription_limit(user_id: UUID, db: Session) -> bool:
    """Check if user has reached their subscription limit"""
    tier = get_user_subscription_tier(user_id, db)
    features = get_subscription_features(tier)
    current_count = get_user_active_subscription_count(user_id, db)

    return current_count < features["max_subscriptions"]
