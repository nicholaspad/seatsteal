"""Stripe payment integration API routes"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from typing import Literal, Optional
import stripe

from db.session import get_db
from models.stripe_customer import StripeCustomer
from models.stripe_subscription import StripeSubscription
from models.user import Profile
from api.middleware.auth import require_auth
from utils.stripe_utils import (
    create_stripe_customer,
    create_checkout_session,
    create_portal_session,
    verify_webhook_signature,
    get_price_id_for_tier,
    get_tier_from_price_id,
)
from config import settings
from utils.errors import log_and_raise_500

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


class CheckoutSessionRequest(BaseModel):
    """Request schema for creating checkout session"""

    tier: Literal["plus", "pro"]


@router.post("/create-checkout-session")
async def create_stripe_checkout_session(
    request: CheckoutSessionRequest,
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a Stripe checkout session for subscription"""
    try:
        # Validate Stripe configuration first
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=500,
                detail="Stripe is not configured. STRIPE_SECRET_KEY is missing.",
            )

        # Get price ID for tier and validate
        price_id = get_price_id_for_tier(request.tier)
        if not price_id:
            raise HTTPException(
                status_code=500,
                detail=f"Stripe price ID for tier '{request.tier}' is not configured.",
            )

        # Get or create Stripe customer
        customer_result = db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == user.id)
        )
        stripe_customer = customer_result.scalar_one_or_none()

        if not stripe_customer:
            # Create new Stripe customer
            customer = await create_stripe_customer(user.email, str(user.id))

            # Save to database
            stripe_customer = StripeCustomer(
                user_id=user.id,
                stripe_customer_id=customer.id,
                email=user.email,
            )
            db.add(stripe_customer)
            db.commit()
            db.refresh(stripe_customer)

        # Create checkout session
        session = await create_checkout_session(
            customer_id=stripe_customer.stripe_customer_id,
            price_id=price_id,
            success_url=f"{settings.FRONTEND_URL}/dashboard?success=true",
            cancel_url=f"{settings.FRONTEND_URL}/#pricing",
            user_id=str(user.id),
        )

        return {
            "success": True,
            "data": {
                "sessionId": session.id,
                "sessionUrl": session.url,
            },
        }

    except HTTPException:
        raise
    except stripe.AuthenticationError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stripe authentication failed. Check STRIPE_SECRET_KEY. Error: {str(e)}",
        )
    except stripe.InvalidRequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid Stripe request. This usually means the price ID is invalid or doesn't exist in your Stripe account. Error: {str(e)}",
        )
    except stripe.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stripe API error: {str(e)}",
        )
    except Exception as e:
        log_and_raise_500("Failed to create checkout session", e)


@router.post("/create-portal-session")
async def create_stripe_portal_session(
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a Stripe billing portal session"""
    try:
        # Get user's Stripe customer
        customer_result = db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == user.id)
        )
        stripe_customer = customer_result.scalar_one_or_none()

        if not stripe_customer:
            raise HTTPException(
                status_code=404,
                detail="No Stripe customer found. Please create a subscription first.",
            )

        # Create portal session
        session = await create_portal_session(
            customer_id=stripe_customer.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard",
        )

        return {
            "success": True,
            "data": {
                "sessionUrl": session.url,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_500("Failed to create portal session", e)


@router.post("/webhooks")
async def stripe_webhooks(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events"""
    try:
        # Get signature from header
        stripe_signature = request.headers.get("stripe-signature")
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="No Stripe signature found")

        # Get raw body as bytes (do not decode)
        payload = await request.body()

        # Verify webhook signature
        event = verify_webhook_signature(payload, stripe_signature)

        # Handle different event types
        if event.type == "customer.created":
            customer = event.data.object
            email = customer.get("email")

            if email:
                # Find user by email
                user_result = db.execute(select(Profile).where(Profile.email == email))
                user = user_result.scalar_one_or_none()

                if user:
                    # Check if customer already exists
                    existing_customer = db.execute(
                        select(StripeCustomer).where(
                            StripeCustomer.stripe_customer_id == customer.id
                        )
                    )
                    if not existing_customer.scalar_one_or_none():
                        # Create customer record
                        stripe_customer = StripeCustomer(
                            user_id=user.id,
                            stripe_customer_id=customer.id,
                            email=email,
                        )
                        db.add(stripe_customer)
                        db.commit()

        elif event.type in [
            "customer.subscription.created",
            "customer.subscription.updated",
        ]:
            subscription = event.data.object
            customer_id = subscription.get("customer")

            # Find user's stripe customer
            customer_result = db.execute(
                select(StripeCustomer).where(
                    StripeCustomer.stripe_customer_id == customer_id
                )
            )
            stripe_customer = customer_result.scalar_one_or_none()

            if stripe_customer:
                # Get price ID
                price_id = subscription["items"]["data"][0]["price"]["id"]
                tier = get_tier_from_price_id(price_id)

                if tier:
                    # Check if subscription exists
                    existing_sub = db.execute(
                        select(StripeSubscription).where(
                            StripeSubscription.stripe_subscription_id == subscription.id
                        )
                    )
                    existing = existing_sub.scalar_one_or_none()

                    if existing:
                        # Update existing subscription
                        existing.status = subscription["status"]
                        existing.price_id = price_id
                        existing.tier = tier
                    else:
                        # Create new subscription
                        stripe_subscription = StripeSubscription(
                            user_id=stripe_customer.user_id,
                            stripe_subscription_id=subscription.id,
                            stripe_customer_id=customer_id,
                            status=subscription["status"],
                            price_id=price_id,
                            tier=tier,
                        )
                        db.add(stripe_subscription)

                    db.commit()

        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object

            # Update subscription status to canceled
            result = db.execute(
                select(StripeSubscription).where(
                    StripeSubscription.stripe_subscription_id == subscription.id
                )
            )
            stripe_subscription = result.scalar_one_or_none()

            if stripe_subscription:
                stripe_subscription.status = "canceled"
                db.commit()

        return {"success": True, "received": True}

    except HTTPException:
        raise
    except ValueError as e:
        # ValueError typically from signature verification - don't expose details
        log_and_raise_500("Invalid webhook request", e)
    except Exception as e:
        log_and_raise_500("Webhook processing failed", e)
