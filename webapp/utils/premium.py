"""Premium subscription utilities for handling user tiers and feature access"""

from typing import Literal
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from uuid import UUID

from models.stripe_subscription import StripeSubscription
from models.subscription import Subscription
from utils.cache import get_cached_user_tier, cache_user_tier

# Subscription tier types
SubscriptionTier = Literal["free", "plus", "pro"]


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


def get_user_subscription_tier(user_id: UUID, db: Session) -> SubscriptionTier:
    """Get the subscription tier for a user based on their active Stripe subscription"""
    user_id_str = str(user_id)

    # Try to get tier from cache first (300s TTL)
    cached_tier = get_cached_user_tier(user_id_str)
    if cached_tier:
        return cached_tier  # type: ignore

    # Cache miss - query for active Stripe subscription
    result = db.execute(
        select(StripeSubscription)
        .where(
            and_(
                StripeSubscription.user_id == user_id,
                StripeSubscription.status.in_(["active", "trialing"]),
            )
        )
        .order_by(StripeSubscription.created_at.desc(), StripeSubscription.id.desc())
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
