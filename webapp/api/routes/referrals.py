"""Referral program API routes"""

import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import stripe

from db.session import get_db
from models.referral import Referral
from models.user import Profile
from models.stripe_customer import StripeCustomer
from api.middleware.auth import require_auth
from config import settings
from utils.errors import log_and_raise_500
from loguru import logger

router = APIRouter(prefix="/api/referrals", tags=["referrals"])

# Referral reward: 1 week of Pro free
REFERRAL_REWARD_DESCRIPTION = "1 week Pro free - Referral reward"
REFERRAL_TRIAL_DAYS = 7


def generate_referral_code(length: int = 8) -> str:
    """Generate a unique referral code"""
    alphabet = string.ascii_uppercase + string.digits
    # Remove ambiguous characters
    alphabet = (
        alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


class ReferralResponse(BaseModel):
    """Response schema for referral info"""

    referral_code: str
    referral_url: str
    total_referrals: int
    successful_referrals: int


class ApplyReferralRequest(BaseModel):
    """Request schema for applying a referral code"""

    referral_code: str


class ApplyReferralResponse(BaseModel):
    """Response schema for applying a referral code"""

    success: bool
    message: str


@router.get("/my-referral")
async def get_my_referral(
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get or create the user's referral code and stats"""
    try:
        # Check if user already has a referral code
        result = db.execute(
            select(Referral).where(
                Referral.referrer_id == user.id,
                Referral.referee_id.is_(None),  # Unused referral codes
            )
        )
        existing_referral = result.scalar_one_or_none()

        if not existing_referral:
            # Create a new referral code
            while True:
                code = generate_referral_code()
                # Check if code already exists
                check = db.execute(
                    select(Referral).where(Referral.referral_code == code)
                )
                if not check.scalar_one_or_none():
                    break

            new_referral = Referral(
                referrer_id=user.id,
                referral_code=code,
            )
            db.add(new_referral)
            db.commit()
            db.refresh(new_referral)
            referral_code = code
        else:
            referral_code = existing_referral.referral_code

        # Get referral stats
        total_result = db.execute(
            select(Referral).where(
                Referral.referrer_id == user.id,
                Referral.referee_id.isnot(None),
            )
        )
        total_referrals = len(total_result.scalars().all())

        successful_result = db.execute(
            select(Referral).where(
                Referral.referrer_id == user.id,
                Referral.referrer_rewarded == True,
            )
        )
        successful_referrals = len(successful_result.scalars().all())

        referral_url = f"{settings.effective_frontend_url}/?ref={referral_code}"

        return {
            "success": True,
            "data": ReferralResponse(
                referral_code=referral_code,
                referral_url=referral_url,
                total_referrals=total_referrals,
                successful_referrals=successful_referrals,
            ),
        }

    except Exception as e:
        log_and_raise_500("Failed to get referral info", e)


@router.post("/apply")
async def apply_referral_code(
    request: ApplyReferralRequest,
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Apply a referral code to get 1 week of Pro free"""
    try:
        code = request.referral_code.upper().strip()

        # Find the referral
        result = db.execute(
            select(Referral).where(
                Referral.referral_code == code,
                Referral.referee_id.is_(None),  # Not yet used
            )
        )
        referral = result.scalar_one_or_none()

        if not referral:
            raise HTTPException(
                status_code=400,
                detail="Invalid or already used referral code",
            )

        # Check user isn't referring themselves
        if referral.referrer_id == user.id:
            raise HTTPException(
                status_code=400,
                detail="You cannot use your own referral code",
            )

        # Check if user has already used a referral code
        existing_referee = db.execute(
            select(Referral).where(Referral.referee_id == user.id)
        )
        if existing_referee.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="You have already used a referral code",
            )

        # Mark the referral as used
        referral.referee_id = user.id
        referral.used_at = db.execute(select(db.func.now())).scalar()

        # Create a new unused referral code for the referrer
        while True:
            new_code = generate_referral_code()
            check = db.execute(
                select(Referral).where(Referral.referral_code == new_code)
            )
            if not check.scalar_one_or_none():
                break

        new_referral = Referral(
            referrer_id=referral.referrer_id,
            referral_code=new_code,
        )
        db.add(new_referral)

        db.commit()

        return {
            "success": True,
            "data": ApplyReferralResponse(
                success=True,
                message="Referral code applied! You'll both get 1 week of Pro free when you subscribe.",
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_500("Failed to apply referral code", e)


@router.get("/validate/{code}")
async def validate_referral_code(
    code: str,
    db: Session = Depends(get_db),
):
    """Validate a referral code (no auth required - for signup flow)"""
    try:
        code = code.upper().strip()

        result = db.execute(
            select(Referral).where(
                Referral.referral_code == code,
                Referral.referee_id.is_(None),
            )
        )
        referral = result.scalar_one_or_none()

        return {
            "success": True,
            "data": {
                "valid": referral is not None,
                "code": code if referral else None,
            },
        }

    except Exception as e:
        log_and_raise_500("Failed to validate referral code", e)


async def create_referral_coupon() -> str:
    """Create a Stripe coupon for referral reward (1 week Pro free)"""
    if not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured, skipping coupon creation")
        return ""

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        # Create a coupon for 100% off for 7 days
        coupon = stripe.Coupon.create(
            percent_off=100,
            duration="once",
            name=REFERRAL_REWARD_DESCRIPTION,
            metadata={"type": "referral_reward"},
        )
        return coupon.id
    except stripe.StripeError as e:
        logger.error(f"Failed to create referral coupon: {e}")
        return ""


async def apply_referral_rewards(
    referral: Referral,
    db: Session,
) -> None:
    """Apply rewards to both referrer and referee after successful subscription"""
    if not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured, skipping referral rewards")
        return

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        # Get Stripe customers for both users
        referrer_customer = db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == referral.referrer_id)
        ).scalar_one_or_none()

        referee_customer = db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == referral.referee_id)
        ).scalar_one_or_none()

        # Create coupon for referee (if they have a Stripe customer)
        if referee_customer and not referral.referee_rewarded:
            try:
                coupon_id = await create_referral_coupon()
                if coupon_id:
                    # Apply coupon to customer for next invoice
                    stripe.Customer.modify(
                        referee_customer.stripe_customer_id,
                        coupon=coupon_id,
                    )
                    referral.referee_coupon_id = coupon_id
                    referral.referee_rewarded = True
                    logger.info(
                        f"Applied referral reward to referee {referral.referee_id}"
                    )
            except stripe.StripeError as e:
                logger.error(f"Failed to apply referee reward: {e}")

        # Create coupon for referrer (if they have a Stripe customer)
        if referrer_customer and not referral.referrer_rewarded:
            try:
                coupon_id = await create_referral_coupon()
                if coupon_id:
                    stripe.Customer.modify(
                        referrer_customer.stripe_customer_id,
                        coupon=coupon_id,
                    )
                    referral.referrer_coupon_id = coupon_id
                    referral.referrer_rewarded = True
                    logger.info(
                        f"Applied referral reward to referrer {referral.referrer_id}"
                    )
            except stripe.StripeError as e:
                logger.error(f"Failed to apply referrer reward: {e}")

        db.commit()

    except Exception as e:
        logger.error(f"Failed to apply referral rewards: {e}")
