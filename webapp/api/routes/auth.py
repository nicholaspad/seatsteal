from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from db.session import get_db
from models.user import Profile
from models.college import College
from models.early_access_email import EarlyAccessEmail
from api.middleware.auth import require_auth, supabase
from config import settings
from utils.errors import log_and_raise_500
from utils.cache import invalidate_user_caches

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UpdateCollegeRequest(BaseModel):
    """Request schema for updating user's college"""

    college_id: int = Field(..., alias="collegeId")

    model_config = ConfigDict(populate_by_name=True)


@router.patch("/update-college")
async def update_college(
    request: UpdateCollegeRequest,
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update the authenticated user's college selection"""
    try:
        # Verify college exists
        college = db.get(College, request.college_id)
        if not college:
            raise HTTPException(status_code=404, detail="College not found")

        if not college.is_active:
            raise HTTPException(status_code=400, detail="College is not active")

        # Update user's college
        user.college_id = request.college_id
        db.commit()
        db.refresh(user)

        # Invalidate user caches (profile and tier) after update
        invalidate_user_caches(str(user.id))

        return {
            "success": True,
            "message": "College updated successfully",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "collegeId": user.college_id,
                "role": user.role,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_and_raise_500("Failed to update college", e)


class AdminSignInRequest(BaseModel):
    """Request schema for admin sign-in"""

    email: EmailStr


@router.post("/admin-signin")
async def admin_signin(
    request: AdminSignInRequest,
    db: Session = Depends(get_db),
):
    """Send admin magic link sign-in email"""
    try:
        # Check if user exists and has admin role
        result = db.execute(
            select(Profile).where(Profile.email == request.email).limit(1)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Access denied. Admin privileges required.",
            )

        # Send magic link using Supabase
        # The Python Supabase SDK raises exceptions on errors (unlike JS SDK)
        try:
            auth_response = supabase.auth.sign_in_with_otp(
                {
                    "email": request.email,
                    "options": {
                        "email_redirect_to": f"{settings.effective_frontend_url}/auth/callback?admin=true"
                    },
                }
            )
        except Exception as supabase_error:
            error_msg = str(supabase_error)
            # Check if it's a rate limit error from Supabase exception
            if (
                "rate limit" in error_msg.lower()
                or "security purposes" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=429, detail="Too many requests. Please try again later."
                )
            # Re-raise other Supabase exceptions to be caught by outer handler
            raise

        return {
            "success": True,
            "message": "Admin magic link sent successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_500("Failed to send admin sign-in email", e)


class CheckEarlyAccessRequest(BaseModel):
    """Request schema for checking early access"""

    email: EmailStr


@router.post("/check-early-access")
async def check_early_access(
    request: CheckEarlyAccessRequest,
    db: Session = Depends(get_db),
):
    """Check if email has early access"""
    try:
        # Validate .edu domain
        if not request.email.endswith(".edu"):
            raise HTTPException(
                status_code=400,
                detail="Please use a valid .edu email address",
            )

        # TEMPORARILY DISABLED: Allow all users to sign up
        # Check if email is in early access list
        # result = db.execute(
        #     select(EarlyAccessEmail).where(
        #         and_(
        #             EarlyAccessEmail.email == request.email,
        #             EarlyAccessEmail.is_active == True,
        #         )
        #     )
        # )
        # early_access = result.scalar_one_or_none()

        return {
            "hasEarlyAccess": True,  # Temporarily allow all users
            "email": request.email,
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_500("Failed to check early access status", e)
