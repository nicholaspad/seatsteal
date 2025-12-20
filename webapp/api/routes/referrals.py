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
from models.referral_redemption import ReferralRedemption
from models.user import Profile
from models.stripe_customer import StripeCustomer
from api.middleware.auth import require_auth
from config import settings
from utils.errors import log_and_raise_500
from utils.stripe_utils import create_stripe_customer
from utils.cache import invalidate_user_caches
from utils.referral_trials import create_referee_trial, create_referrer_trial
from loguru import logger

router = APIRouter(prefix="/api/referrals", tags=["referrals"])

# Referral reward: 1 week of Pro free
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
        # Find user's referral code (one per user)
        result = db.execute(select(Referral).where(Referral.referrer_id == user.id))
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
            referral_id = new_referral.id
        else:
            referral_code = existing_referral.referral_code
            referral_id = existing_referral.id

        # Count redemptions
        total_redemptions = db.execute(
            select(func.count(ReferralRedemption.id)).where(
                ReferralRedemption.referral_id == referral_id
            )
        ).scalar()

        successful_redemptions = db.execute(
            select(func.count(ReferralRedemption.id)).where(
                ReferralRedemption.referral_id == referral_id,
                ReferralRedemption.referee_trial_subscription_id.isnot(None),
            )
        ).scalar()

        referral_url = f"{settings.effective_frontend_url}/?ref={referral_code}"

        return {
            "success": True,
            "data": ReferralResponse(
                referral_code=referral_code,
                referral_url=referral_url,
                total_referrals=total_redemptions or 0,
                successful_referrals=successful_redemptions or 0,
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
    """Apply a referral code to get 7-day Pro trial for both users immediately"""
    try:
        code = request.referral_code.upper().strip()

        # Find the referral code (codes are reusable)
        result = db.execute(select(Referral).where(Referral.referral_code == code))
        referral = result.scalar_one_or_none()

        if not referral:
            raise HTTPException(
                status_code=400,
                detail="Invalid referral code",
            )

        # Check user isn't referring themselves
        if referral.referrer_id == user.id:
            raise HTTPException(
                status_code=400,
                detail="You cannot use your own referral code",
            )

        # Check if this user already used THIS specific code
        existing_redemption = db.execute(
            select(ReferralRedemption).where(
                ReferralRedemption.referral_id == referral.id,
                ReferralRedemption.referee_id == user.id,
            )
        ).scalar_one_or_none()

        if existing_redemption:
            raise HTTPException(
                status_code=400,
                detail="You have already used this referral code",
            )

        # Create redemption record
        redemption = ReferralRedemption(
            referral_id=referral.id,
            referee_id=user.id,
        )
        db.add(redemption)
        db.flush()  # Get redemption.id

        # Create trials for both users immediately
        referee_sub_id = await create_referee_trial(user.id, redemption, db)
        referrer_sub_id = await create_referrer_trial(
            referral.referrer_id, redemption, db
        )

        db.commit()

        # Invalidate tier caches for both users
        invalidate_user_caches(str(user.id))
        invalidate_user_caches(str(referral.referrer_id))

        return {
            "success": True,
            "data": ApplyReferralResponse(
                success=True,
                message="🎉 Your referral has been applied. You and your referrer have received 7 days of Pro access!",
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

        result = db.execute(select(Referral).where(Referral.referral_code == code))
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
