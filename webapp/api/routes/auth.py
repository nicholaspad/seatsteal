from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr

from ...db.session import get_db
from ...models.user import Profile
from ...models.college import College
from ...models.early_access_email import EarlyAccessEmail
from ...api.middleware.auth import require_auth, supabase
from ...config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UpdateCollegeRequest(BaseModel):
    """Request schema for updating user's college"""

    college_id: int


@router.patch("/update-college")
async def update_college(
    request: UpdateCollegeRequest,
    user: Profile = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's college selection"""
    try:
        # Verify college exists
        college = await db.get(College, request.college_id)
        if not college:
            raise HTTPException(status_code=404, detail="College not found")

        if not college.is_active:
            raise HTTPException(status_code=400, detail="College is not active")

        # Update user's college
        user.college_id = request.college_id
        await db.commit()
        await db.refresh(user)

        return {
            "success": True,
            "message": "College updated successfully",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "college_id": user.college_id,
                "role": user.role,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update college: {str(e)}",
        )


class AdminSignInRequest(BaseModel):
    """Request schema for admin sign-in"""

    email: EmailStr


@router.post("/admin-signin")
async def admin_signin(
    request: AdminSignInRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send admin magic link sign-in email"""
    try:
        # Check if user exists and has admin role
        result = await db.execute(
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
        auth_response = supabase.auth.sign_in_with_otp(
            {
                "email": request.email,
                "options": {
                    "email_redirect_to": f"{settings.FRONTEND_URL}/auth/admin-callback"
                },
            }
        )

        if auth_response.error:
            raise HTTPException(status_code=500, detail="Failed to send magic link")

        return {"message": "Admin magic link sent successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


class CheckEarlyAccessRequest(BaseModel):
    """Request schema for checking early access"""

    email: EmailStr


@router.post("/check-early-access")
async def check_early_access(
    request: CheckEarlyAccessRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check if email has early access"""
    try:
        # Validate .edu domain
        if not request.email.endswith(".edu"):
            raise HTTPException(
                status_code=400,
                detail="Please use a valid .edu email address",
            )

        # Check if email is in early access list
        result = await db.execute(
            select(EarlyAccessEmail).where(
                and_(
                    EarlyAccessEmail.email == request.email,
                    EarlyAccessEmail.is_active == True,
                )
            )
        )
        early_access = result.scalar_one_or_none()

        return {
            "hasEarlyAccess": early_access is not None,
            "email": request.email,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check early access status: {str(e)}",
        )
