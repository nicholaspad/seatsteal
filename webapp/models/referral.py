from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base


class Referral(Base):
    """Referrals table - Each user has one reusable referral code

    The referral code can be used by multiple people. Each use is tracked
    in the referral_redemptions table.
    """

    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)

    # The user who owns this referral code
    referrer_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True
    )

    # Unique referral code for sharing (reusable)
    referral_code = Column(String(20), nullable=False, unique=True, index=True)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    redemptions = relationship("ReferralRedemption", back_populates="referral")

    __table_args__ = (Index("referrals_referrer_id_idx", "referrer_id"),)
