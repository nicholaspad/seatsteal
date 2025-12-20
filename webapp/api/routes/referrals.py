"""Referral program API routes"""

import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
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
from utils.stripe_utils import create_stripe_customer
from utils.cache import invalidate_user_caches
from loguru import logger

router = APIRouter(prefix="/api/referrals", tags=["referrals"])

# Referral reward: 100% off first month (monthly subscriptions only)
REFERRAL_REWARD_DESCRIPTION = "100% off first month - Referral reward"


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
        referral.used_at = db.execute(select(func.now())).scalar()

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
                message="Referral code applied! You'll both get 100% off your first month when you subscribe to a monthly plan.",
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
    """Create a Stripe coupon for referral reward (100% off first month, monthly plans only)"""
    if not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured, skipping coupon creation")
        return ""

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        # Get product IDs from monthly price IDs
        monthly_product_ids = []

        if settings.STRIPE_PLUS_PRICE_ID:
            try:
                plus_price = stripe.Price.retrieve(settings.STRIPE_PLUS_PRICE_ID)
                monthly_product_ids.append(plus_price.product)
            except stripe.StripeError as e:
                logger.warning(f"Failed to retrieve Plus monthly price: {e}")

        if settings.STRIPE_PRO_PRICE_ID:
            try:
                pro_price = stripe.Price.retrieve(settings.STRIPE_PRO_PRICE_ID)
                monthly_product_ids.append(pro_price.product)
            except stripe.StripeError as e:
                logger.warning(f"Failed to retrieve Pro monthly price: {e}")

        if not monthly_product_ids:
            logger.error("No monthly product IDs found for referral coupon")
            return ""

        # Create a coupon restricted to monthly products only
        coupon = stripe.Coupon.create(
            percent_off=100,
            duration="once",
            name=REFERRAL_REWARD_DESCRIPTION,
            applies_to={
                "products": monthly_product_ids
            },  # 🔒 Only applies to monthly products
            metadata={"type": "referral_reward"},
        )
        logger.info(
            f"Created referral coupon {coupon.id} for products: {monthly_product_ids}"
        )
        return coupon.id
    except stripe.StripeError as e:
        logger.error(f"Failed to create referral coupon: {e}")
        return ""


async def get_or_create_stripe_customer(
    user_id, db: Session
) -> Optional[StripeCustomer]:
    """Get or create a Stripe customer for a user"""
    # Check if customer already exists
    customer = db.execute(
        select(StripeCustomer).where(StripeCustomer.user_id == user_id)
    ).scalar_one_or_none()

    if customer:
        return customer

    # Get user profile to get email
    user = db.execute(select(Profile).where(Profile.id == user_id)).scalar_one_or_none()

    if not user:
        logger.error(f"User {user_id} not found when creating Stripe customer")
        return None

    try:
        # Create Stripe customer
        stripe_customer = await create_stripe_customer(user.email, str(user_id))

        # Save to database
        new_customer = StripeCustomer(
            user_id=user_id,
            stripe_customer_id=stripe_customer.id,
            email=user.email,
        )
        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)

        # Invalidate user caches
        invalidate_user_caches(str(user_id))

        logger.info(f"Created Stripe customer for user {user_id}")
        return new_customer
    except Exception as e:
        logger.error(f"Failed to create Stripe customer for user {user_id}: {e}")
        return None


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
        # Get or create Stripe customers for both users
        referee_customer = await get_or_create_stripe_customer(referral.referee_id, db)
        referrer_customer = await get_or_create_stripe_customer(
            referral.referrer_id, db
        )

        # Create coupon for referee
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

        # Create coupon for referrer
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
