from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from models.base import Base


class Referral(Base):
    """Referrals table - Tracks user referrals and rewards"""

    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)

    # The user who created the referral code
    referrer_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True
    )

    # Unique referral code for sharing
    referral_code = Column(String(20), nullable=False, unique=True, index=True)

    # The user who signed up using this referral (null until used)
    referee_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True, index=True
    )

    # Whether rewards have been applied
    referrer_rewarded = Column(Boolean, default=False, nullable=False)
    referee_rewarded = Column(Boolean, default=False, nullable=False)

    # Stripe coupon IDs for tracking
    referrer_coupon_id = Column(String, nullable=True)
    referee_coupon_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("referrals_referrer_id_idx", "referrer_id"),
        Index("referrals_referee_id_idx", "referee_id"),
    )
