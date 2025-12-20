"""Referral trial management utilities

Handles creation and management of trial subscriptions for the referral program.
When a user applies a referral code, both the referee and referrer receive
7-day Pro trials.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
import stripe
from sqlalchemy.orm import Session

from models.referral_redemption import ReferralRedemption
from utils.stripe_utils import (
    create_trial_subscription,
    extend_subscription_trial,
    get_price_id_for_tier,
)
from utils.premium import get_user_subscription_tier, invalidate_user_caches
from utils.database import get_stripe_customer

logger = logging.getLogger(__name__)


async def create_referee_trial(
    user_id: UUID, redemption: ReferralRedemption, db: Session
) -> Optional[str]:
    """Create a 7-day Pro trial subscription for the referee (user who used the code)

    Args:
        user_id: UUID of the referee
        redemption: ReferralRedemption record being processed
        db: Database session

    Returns:
        Stripe subscription ID if successful, None otherwise
    """
    try:
        # Get or create Stripe customer
        stripe_customer = await get_stripe_customer(user_id, db)
        if not stripe_customer:
            logger.error(f"Failed to get Stripe customer for referee {user_id}")
            return None

        # Create Pro trial subscription
        subscription = await create_trial_subscription(
            customer_id=stripe_customer.stripe_customer_id,
            tier="pro",
            trial_days=7,
            user_id=str(user_id),
            metadata={"redemption_id": redemption.id, "role": "referee"},
        )

        # Store subscription ID and trial end date
        redemption.referee_trial_subscription_id = subscription.id
        redemption.referee_trial_end = datetime.fromtimestamp(subscription.trial_end)

        logger.info(
            f"Created referee trial subscription {subscription.id} for user {user_id}"
        )
        return subscription.id

    except Exception as e:
        logger.error(
            f"Failed to create referee trial for user {user_id}: {e}", exc_info=True
        )
        return None


async def create_referrer_trial(
    referrer_id: UUID, redemption: ReferralRedemption, db: Session
) -> Optional[str]:
    """Create or extend a 7-day Pro trial for the referrer (user who owns the code)

    If the referrer is on free tier, creates a new Pro trial.
    If they have an active subscription, extends it by 7 days.

    Args:
        referrer_id: UUID of the referrer
        redemption: ReferralRedemption record being processed
        db: Database session

    Returns:
        Stripe subscription ID if successful, None otherwise
    """
    try:
        # Get referrer's current tier
        current_tier = await get_user_subscription_tier(referrer_id, db)
        redemption.referrer_previous_tier = current_tier

        # Get or create Stripe customer
        stripe_customer = await get_stripe_customer(referrer_id, db)
        if not stripe_customer:
            logger.error(f"Failed to get Stripe customer for referrer {referrer_id}")
            return None

        # Check if referrer has an active subscription
        subscriptions = stripe.Subscription.list(
            customer=stripe_customer.stripe_customer_id,
            status="active",
            limit=1,
        )

        if current_tier == "free" or not subscriptions.data:
            # Referrer is on free tier - create new Pro trial
            subscription = await create_trial_subscription(
                customer_id=stripe_customer.stripe_customer_id,
                tier="pro",
                trial_days=7,
                user_id=str(referrer_id),
                metadata={"redemption_id": redemption.id, "role": "referrer"},
            )

            redemption.referrer_trial_subscription_id = subscription.id
            redemption.referrer_trial_end = datetime.fromtimestamp(
                subscription.trial_end
            )

            logger.info(
                f"Created referrer trial subscription {subscription.id} for user {referrer_id}"
            )

        else:
            # Referrer has active subscription - extend trial by 7 days
            existing_subscription = subscriptions.data[0]

            # Upgrade to Pro tier if not already Pro
            pro_price_id = get_price_id_for_tier("pro", "monthly")
            if existing_subscription.items.data[0].price.id != pro_price_id:
                stripe.Subscription.modify(
                    existing_subscription.id,
                    items=[
                        {
                            "id": existing_subscription.items.data[0].id,
                            "price": pro_price_id,
                        }
                    ],
                )

            # Extend trial
            subscription = await extend_subscription_trial(
                existing_subscription.id, additional_days=7
            )

            redemption.referrer_trial_subscription_id = subscription.id
            redemption.referrer_trial_end = datetime.fromtimestamp(
                subscription.trial_end
            )

            logger.info(
                f"Extended trial for referrer subscription {subscription.id} by 7 days"
            )

        # Invalidate tier cache so referrer sees Pro tier immediately
        invalidate_user_caches(referrer_id)

        return redemption.referrer_trial_subscription_id

    except Exception as e:
        logger.error(
            f"Failed to create/extend referrer trial for user {referrer_id}: {e}",
            exc_info=True,
        )
        return None
