"""ReferralRedemption model for tracking each use of a referral code"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base


class ReferralRedemption(Base):
    """Tracks each time a referral code is used

    Each referral code can be used by multiple people, but each person
    can only use a specific referral code once. When a code is redeemed,
    both the referrer and referee receive 7-day Pro trials.
    """

    __tablename__ = "referral_redemptions"

    id = Column(Integer, primary_key=True)
    referral_id = Column(
        Integer, ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False
    )
    referee_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Trial tracking
    referee_trial_subscription_id = Column(String, nullable=True)
    referrer_trial_subscription_id = Column(String, nullable=True)
    referrer_previous_tier = Column(String, nullable=True)
    referrer_trial_end = Column(DateTime(timezone=True), nullable=True)
    referee_trial_end = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    referral = relationship("Referral", back_populates="redemptions")

    # Constraints
    __table_args__ = (
        UniqueConstraint("referral_id", "referee_id", name="uq_referral_referee"),
    )
