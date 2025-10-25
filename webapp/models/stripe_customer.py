from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from models.base import Base


class StripeCustomer(Base):
    """Stripe customers table - Links users to Stripe customer IDs"""

    __tablename__ = "stripe_customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, unique=True
    )  # One-to-one relationship with users
    stripe_customer_id = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
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
        Index("stripe_customers_user_id_idx", "user_id", unique=True),
        Index("stripe_customers_stripe_id_idx", "stripe_customer_id", unique=True),
    )
