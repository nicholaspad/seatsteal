"""Database utility functions"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.user import Profile
from models.stripe_customer import StripeCustomer
from utils.stripe_utils import create_stripe_customer
from utils.cache import invalidate_user_caches

logger = logging.getLogger(__name__)


async def get_stripe_customer(user_id: UUID, db: Session) -> Optional[StripeCustomer]:
    """Get or create a Stripe customer for a user

    Args:
        user_id: UUID of the user
        db: Database session

    Returns:
        StripeCustomer object if successful, None otherwise
    """
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
