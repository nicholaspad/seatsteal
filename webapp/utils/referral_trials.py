"""Referral trial management utilities

Handles creation and management of trial subscriptions for the referral program.
When a user applies a referral code, both the referee and referrer receive
7-day Pro trials.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime
from uuid import UUID
import stripe
from sqlalchemy.orm import Session

from models.referral_redemption import ReferralRedemption
from utils.stripe_utils import (
    create_trial_subscription,
    extend_subscription_trial,
)
from utils.premium import (
    PAID_STRIPE_STATUSES,
    get_user_subscription_tier,
    pick_highest_paid_stripe_subscription,
)
from utils.cache import invalidate_user_caches
from utils.database import get_stripe_customer

logger = logging.getLogger(__name__)

# Statuses we can safely extend with trial_end. past_due is paid for
# tier lookup, but Stripe rejects trial_end updates on past_due, and
# creating a second Pro trial on top of it would double-bill.
EXTENDABLE_STRIPE_STATUSES = ("active", "trialing")


def _referral_trial_action(subscriptions) -> Tuple[str, Optional[object]]:
    """Decide how to apply a referral trial given the customer's Stripe subs.

    Returns one of:
        ("extend", sub)        — active/trialing: extend the highest paid plan
        ("skip_past_due", sub) — past_due only: skip (do not create or extend)
        ("create", None)       — no paid sub: create a new Pro trial

    past_due is an explicit branch so it cannot fall through to create.
    Reapplying the skipped reward when the sub later becomes active would
    need a pending-reward row (new table or column) so the Stripe webhook
    can find it. That is a migration; we skip reapply and only log.
    """
    paid = [sub for sub in subscriptions.data if sub.status in PAID_STRIPE_STATUSES]
    extendable = [sub for sub in paid if sub.status in EXTENDABLE_STRIPE_STATUSES]
    past_due = [sub for sub in paid if sub.status == "past_due"]

    if extendable:
        return "extend", pick_highest_paid_stripe_subscription(extendable)
    if past_due:
        return "skip_past_due", pick_highest_paid_stripe_subscription(past_due)
    return "create", None


def _log_skipped_past_due_reward(user_id: UUID, subscription_id: str) -> None:
    logger.warning(
        "Skipping referral trial reward user_id=%s subscription_id=%s reason=past_due",
        user_id,
        subscription_id,
    )


async def create_referee_trial(
    user_id: UUID, redemption: ReferralRedemption, db: Session
) -> Optional[str]:
    """Create a 7-day Pro trial subscription for the referee (user who used the code)

    If referee has no paid Stripe subscription, creates a new Pro trial.
    If they already have an active or trialing subscription, extends it by
    7 days instead of creating a second Pro trial.
    If they only have a past_due subscription, skips the reward (extending
    past_due is invalid; creating a new trial would double-bill).

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

        subscriptions = stripe.Subscription.list(
            customer=stripe_customer.stripe_customer_id,
            limit=10,
        )

        action, existing_subscription = _referral_trial_action(subscriptions)

        if action == "extend":
            subscription = await extend_subscription_trial(
                existing_subscription.id, additional_days=7
            )
            logger.info(
                f"Extended trial for referee subscription {subscription.id} by 7 days"
            )
        elif action == "skip_past_due":
            _log_skipped_past_due_reward(user_id, existing_subscription.id)
            return None
        else:
            subscription = await create_trial_subscription(
                customer_id=stripe_customer.stripe_customer_id,
                tier="pro",
                trial_days=7,
                user_id=str(user_id),
                metadata={"redemption_id": redemption.id, "role": "referee"},
            )
            logger.info(
                f"Created referee trial subscription {subscription.id} for user {user_id}"
            )

        # Store subscription ID and trial end date
        redemption.referee_trial_subscription_id = subscription.id
        redemption.referee_trial_end = datetime.fromtimestamp(subscription.trial_end)

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

    If the referrer has no paid Stripe subscription, creates a new Pro trial.
    If they already have an active or trialing subscription, extends it by
    7 days instead of creating a second Pro trial.
    If they only have a past_due subscription, skips the reward (extending
    past_due is invalid; creating a new trial would double-bill).

    Args:
        referrer_id: UUID of the referrer
        redemption: ReferralRedemption record being processed
        db: Database session

    Returns:
        Stripe subscription ID if successful, None otherwise
    """
    try:
        # Get referrer's current tier
        current_tier = get_user_subscription_tier(referrer_id, db)
        redemption.referrer_previous_tier = current_tier

        # Get or create Stripe customer
        stripe_customer = await get_stripe_customer(referrer_id, db)
        if not stripe_customer:
            logger.error(f"Failed to get Stripe customer for referrer {referrer_id}")
            return None

        subscriptions = stripe.Subscription.list(
            customer=stripe_customer.stripe_customer_id,
            limit=10,
        )

        action, existing_subscription = _referral_trial_action(subscriptions)

        if action == "extend":
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
        elif action == "skip_past_due":
            _log_skipped_past_due_reward(referrer_id, existing_subscription.id)
            return None
        else:
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

        # Invalidate tier cache so referrer sees Pro tier immediately
        invalidate_user_caches(referrer_id)

        return redemption.referrer_trial_subscription_id

    except Exception as e:
        logger.error(
            f"Failed to create/extend referrer trial for user {referrer_id}: {e}",
            exc_info=True,
        )
        return None
