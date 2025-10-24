"""Premium subscription utilities for handling user tiers and feature access"""

from typing import Literal
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from uuid import UUID

from ..models.stripe_subscription import StripeSubscription
from ..models.subscription import Subscription

# Subscription tier types
SubscriptionTier = Literal["free", "plus", "pro"]


# Feature limits per tier
TIER_FEATURES = {
    "free": {
        "max_subscriptions": 3,
        "has_enrollment_analysis": False,
        "has_course_summary": False,
        "has_priority_notifications": False,
    },
    "plus": {
        "max_subscriptions": 10,
        "has_enrollment_analysis": True,
        "has_course_summary": True,
        "has_priority_notifications": False,
    },
    "pro": {
        "max_subscriptions": 50,
        "has_enrollment_analysis": True,
        "has_course_summary": True,
        "has_priority_notifications": True,
    },
}


def get_user_subscription_tier(
    user_id: UUID, db: Session
) -> SubscriptionTier:
    """Get the subscription tier for a user based on their active Stripe subscription"""
    # Query for active Stripe subscription
    result = db.execute(
        select(StripeSubscription)
        .where(
            and_(
                StripeSubscription.user_id == user_id,
                StripeSubscription.status == "active",
            )
        )
        .order_by(StripeSubscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return "free"

    # Return tier from subscription
    return subscription.tier  # type: ignore


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


def check_subscription_limit(user_id: UUID, db: Session) -> bool:
    """Check if user has reached their subscription limit"""
    tier = get_user_subscription_tier(user_id, db)
    features = get_subscription_features(tier)
    current_count = get_user_active_subscription_count(user_id, db)

    return current_count < features["max_subscriptions"]
