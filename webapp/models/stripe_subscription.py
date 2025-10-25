from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from models.base import Base


class StripeSubscription(Base):
    """Stripe subscriptions table - Tracks active Stripe subscriptions"""

    __tablename__ = "stripe_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True
    )
    stripe_subscription_id = Column(String, nullable=False, unique=True)
    stripe_customer_id = Column(
        String, ForeignKey("stripe_customers.stripe_customer_id"), nullable=False
    )

    # Subscription details
    status = Column(String, nullable=False)  # active, canceled, incomplete, etc.
    price_id = Column(String, nullable=False)  # Stripe price ID
    tier = Column(String, nullable=False)  # plus, pro (derived from price ID)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("stripe_subscriptions_user_id_idx", "user_id"),
        Index(
            "stripe_subscriptions_stripe_id_idx", "stripe_subscription_id", unique=True
        ),
        Index("stripe_subscriptions_status_idx", "status"),
    )
