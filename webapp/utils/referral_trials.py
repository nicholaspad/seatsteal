"""Referral trial management utilities

Handles creation and management of trial subscriptions for the referral program.
When a user applies a referral code, both the referee and referrer receive
7-day Pro trials.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple
from uuid import UUID
import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.referral_redemption import ReferralRedemption
from models.stripe_customer import StripeCustomer
from models.user import Profile
from utils.stripe_utils import (
    create_stripe_customer,
    create_trial_subscription,
    extend_subscription_trial,
)
from utils.premium import (
    PAID_STRIPE_STATUSES,
    get_user_subscription_tier,
    pick_highest_paid_stripe_subscription,
)
from utils.cache import invalidate_user_caches
from utils.database import get_stripe_customer  # noqa: F401 — tests patch this name

logger = logging.getLogger(__name__)

# No referral rewards while an invoice is unpaid (past_due).
EXTENDABLE_STRIPE_STATUSES = ("active", "trialing")

REFEREE_PAST_DUE_MESSAGE = "Update your card to claim your free Pro week."


def referral_idempotency_key(referee_id: UUID, role: str) -> str:
    """Stable Stripe Idempotency-Key for a referee+role trial write."""
    return f"referral-trial-{referee_id}-{role}"


def _lookup_stripe_customer(user_id: UUID, db: Session) -> Optional[StripeCustomer]:
    """Inspect-only: do not create or commit a StripeCustomer during planning."""
    return db.execute(
        select(StripeCustomer).where(StripeCustomer.user_id == user_id)
    ).scalar_one_or_none()


async def _ensure_stripe_customer(
    user_id: UUID, db: Session
) -> Optional[StripeCustomer]:
    """Create a Stripe customer if needed without committing the outer transaction."""
    existing = _lookup_stripe_customer(user_id, db)
    if existing:
        return existing

    user = db.execute(select(Profile).where(Profile.id == user_id)).scalar_one_or_none()
    if not user:
        logger.error(f"User {user_id} not found when creating Stripe customer")
        return None

    try:
        stripe_customer = await create_stripe_customer(user.email, str(user_id))
        new_customer = StripeCustomer(
            user_id=user_id,
            stripe_customer_id=stripe_customer.id,
            email=user.email,
        )
        db.add(new_customer)
        db.flush()
        return new_customer
    except Exception as e:
        logger.error(f"Failed to create Stripe customer for user {user_id}: {e}")
        return None


class ReferralTrialAction(str, Enum):
    EXTEND = "extend"
    CREATE = "create"
    SKIP_PAST_DUE = "skip_past_due"
    FAILED = "failed"


class ReferralTrialOutcome(str, Enum):
    GRANTED = "granted"
    SKIPPED_PAST_DUE = "skipped_past_due"
    FAILED = "failed"


@dataclass
class ReferralTrialPlan:
    """Inspect-only decision. No Stripe subscription writes have happened yet."""

    action: ReferralTrialAction
    existing_subscription: Optional[object] = None
    stripe_customer: Optional[StripeCustomer] = None


@dataclass
class ReferralTrialResult:
    """Result of applying a planned referral trial. Skip is not a failure."""

    outcome: ReferralTrialOutcome
    subscription_id: Optional[str] = None


def _referral_trial_action(
    subscriptions,
) -> Tuple[ReferralTrialAction, Optional[object]]:
    """Decide how to apply a referral trial given the customer's Stripe subs.

    Returns one of:
        (EXTEND, sub)        — active/trialing: extend the highest paid plan
        (SKIP_PAST_DUE, sub) — past_due only: skip (do not create or extend)
        (CREATE, None)       — no paid sub: create a new Pro trial

    past_due is an explicit branch so it cannot fall through to create.
    Reapplying the skipped reward when the sub later becomes active would
    need a pending-reward row (new table or column) so the Stripe webhook
    can find it. That is a migration; we skip reapply and only log.
    """
    paid = [sub for sub in subscriptions.data if sub.status in PAID_STRIPE_STATUSES]
    extendable = [sub for sub in paid if sub.status in EXTENDABLE_STRIPE_STATUSES]
    past_due = [sub for sub in paid if sub.status == "past_due"]

    if extendable:
        return (
            ReferralTrialAction.EXTEND,
            pick_highest_paid_stripe_subscription(extendable),
        )
    if past_due:
        return (
            ReferralTrialAction.SKIP_PAST_DUE,
            pick_highest_paid_stripe_subscription(past_due),
        )
    return ReferralTrialAction.CREATE, None


def _log_skipped_past_due_reward(user_id: UUID, subscription_id: Optional[str]) -> None:
    logger.warning(
        "Skipping referral trial reward user_id=%s subscription_id=%s reason=past_due",
        user_id,
        subscription_id,
    )


async def plan_referral_trial(user_id: UUID, db: Session) -> ReferralTrialPlan:
    """Inspect Stripe subscriptions without creating or extending any.

    Missing StripeCustomer means CREATE (apply will create the customer).
    Planning never calls get_stripe_customer, which would commit.
    """
    try:
        stripe_customer = _lookup_stripe_customer(user_id, db)
        if not stripe_customer:
            return ReferralTrialPlan(action=ReferralTrialAction.CREATE)

        subscriptions = stripe.Subscription.list(
            customer=stripe_customer.stripe_customer_id,
            limit=10,
        )
        action, existing = _referral_trial_action(subscriptions)
        return ReferralTrialPlan(
            action=action,
            existing_subscription=existing,
            stripe_customer=stripe_customer,
        )
    except Exception as e:
        logger.error(
            f"Failed to plan referral trial for user {user_id}: {e}",
            exc_info=True,
        )
        return ReferralTrialPlan(action=ReferralTrialAction.FAILED)


async def apply_referral_trial(
    user_id: UUID,
    redemption: ReferralRedemption,
    db: Session,
    *,
    role: str,
    plan: ReferralTrialPlan,
) -> ReferralTrialResult:
    """Apply a previously planned referral trial. Skip does not write to Stripe."""
    try:
        if plan.action == ReferralTrialAction.SKIP_PAST_DUE:
            existing_id = getattr(plan.existing_subscription, "id", None)
            _log_skipped_past_due_reward(user_id, existing_id)
            if role == "referrer":
                redemption.referrer_previous_tier = get_user_subscription_tier(
                    user_id, db
                )
            return ReferralTrialResult(outcome=ReferralTrialOutcome.SKIPPED_PAST_DUE)

        if plan.action == ReferralTrialAction.FAILED:
            return ReferralTrialResult(outcome=ReferralTrialOutcome.FAILED)

        if role == "referrer":
            redemption.referrer_previous_tier = get_user_subscription_tier(user_id, db)

        idempotency_key = referral_idempotency_key(redemption.referee_id, role)

        if plan.action == ReferralTrialAction.EXTEND:
            if not plan.existing_subscription:
                logger.error(
                    f"Missing existing subscription on EXTEND plan for user {user_id}"
                )
                return ReferralTrialResult(outcome=ReferralTrialOutcome.FAILED)
            subscription = await extend_subscription_trial(
                plan.existing_subscription.id,
                additional_days=7,
                idempotency_key=idempotency_key,
            )
            logger.info(
                f"Extended trial for {role} subscription {subscription.id} by 7 days"
            )
        elif plan.action == ReferralTrialAction.CREATE:
            stripe_customer = plan.stripe_customer or await _ensure_stripe_customer(
                user_id, db
            )
            if not stripe_customer:
                logger.error(
                    f"Failed to ensure Stripe customer for referral user {user_id}"
                )
                return ReferralTrialResult(outcome=ReferralTrialOutcome.FAILED)
            subscription = await create_trial_subscription(
                customer_id=stripe_customer.stripe_customer_id,
                tier="pro",
                trial_days=7,
                user_id=str(user_id),
                metadata={"redemption_id": redemption.id, "role": role},
                idempotency_key=idempotency_key,
            )
            logger.info(
                f"Created {role} trial subscription {subscription.id} for user {user_id}"
            )
        else:
            logger.error(
                f"Unknown referral trial action {plan.action} for user {user_id}"
            )
            return ReferralTrialResult(outcome=ReferralTrialOutcome.FAILED)

        if role == "referee":
            redemption.referee_trial_subscription_id = subscription.id
            redemption.referee_trial_end = datetime.fromtimestamp(
                subscription.trial_end
            )
        else:
            redemption.referrer_trial_subscription_id = subscription.id
            redemption.referrer_trial_end = datetime.fromtimestamp(
                subscription.trial_end
            )
            invalidate_user_caches(user_id)

        return ReferralTrialResult(
            outcome=ReferralTrialOutcome.GRANTED,
            subscription_id=subscription.id,
        )
    except Exception as e:
        logger.error(
            f"Failed to apply {role} referral trial for user {user_id}: {e}",
            exc_info=True,
        )
        return ReferralTrialResult(outcome=ReferralTrialOutcome.FAILED)


async def create_referee_trial(
    user_id: UUID, redemption: ReferralRedemption, db: Session
) -> ReferralTrialResult:
    """Create a 7-day Pro trial subscription for the referee (user who used the code)

    Inspects first, then writes. Prefer plan_referral_trial + apply_referral_trial
    in the route so both parties are decided before any Stripe write.
    """
    plan = await plan_referral_trial(user_id, db)
    return await apply_referral_trial(
        user_id, redemption, db, role="referee", plan=plan
    )


async def create_referrer_trial(
    referrer_id: UUID, redemption: ReferralRedemption, db: Session
) -> ReferralTrialResult:
    """Create or extend a 7-day Pro trial for the referrer (user who owns the code)

    Inspects first, then writes. Prefer plan_referral_trial + apply_referral_trial
    in the route so both parties are decided before any Stripe write.
    """
    plan = await plan_referral_trial(referrer_id, db)
    return await apply_referral_trial(
        referrer_id, redemption, db, role="referrer", plan=plan
    )
