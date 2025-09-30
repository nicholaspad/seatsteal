from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Profile(Base):
    """
    User profile table - Simplified for Supabase auth integration.
    The id field matches Supabase auth.users.id directly.
    """

    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True)
    college_id = Column(Integer, ForeignKey("colleges.id"))  # Nullable for new user flow
    role = Column(String, default="user", nullable=False)  # 'user' or 'admin'
    email = Column(String, nullable=False, unique=True, index=True)
    phone = Column(String)

    __table_args__ = (Index("profiles_email_idx", "email", unique=True),)