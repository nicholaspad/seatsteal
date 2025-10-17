"""User settings and profile API routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from ...db.session import get_db
from ...models.user import Profile
from ...models.college import College
from ...api.middleware.auth import require_auth
from ...utils.premium import get_user_subscription_tier

router = APIRouter(prefix="/api/user", tags=["user"])


class UserSettingsResponse(BaseModel):
    """Response schema for user settings"""

    email: str
    phone: str
    collegeId: int
    collegeName: str


@router.get("/settings")
async def get_user_settings(
    user: Profile = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get user settings"""
    try:
        # Get college details if user has a college
        college = None
        if user.college_id:
            college_result = await db.execute(
                select(College).where(College.id == user.college_id)
            )
            college = college_result.scalar_one_or_none()

        return {
            "success": True,
            "data": {
                "email": user.email,
                "phone": user.phone or "",
                "collegeId": user.college_id or 0,
                "collegeName": college.name if college else "",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch user settings: {str(e)}"
        )


class UpdateUserSettingsRequest(BaseModel):
    """Request schema for updating user settings"""

    phone: Optional[str] = None
    collegeId: Optional[int] = None


@router.put("/settings")
async def update_user_settings(
    request: UpdateUserSettingsRequest,
    user: Profile = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings"""
    try:
        # Verify college exists if provided
        college = None
        if request.collegeId and request.collegeId > 0:
            college_result = await db.execute(
                select(College).where(College.id == request.collegeId)
            )
            college = college_result.scalar_one_or_none()

            if not college:
                raise HTTPException(status_code=404, detail="College not found")

        # Track if college changed
        old_college_id = user.college_id
        college_changed = request.collegeId != old_college_id

        # Update user settings
        if request.phone is not None:
            user.phone = request.phone
        if request.collegeId is not None:
            user.college_id = request.collegeId

        await db.commit()
        await db.refresh(user)

        return {
            "success": True,
            "data": {
                "email": user.email,
                "phone": user.phone or "",
                "collegeId": user.college_id or 0,
                "collegeName": college.name if college else "",
            },
            "collegeChanged": college_changed,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update user settings: {str(e)}"
        )


@router.get("/subscription-tier")
async def get_subscription_tier(
    user: Profile = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get user's subscription tier"""
    try:
        tier = await get_user_subscription_tier(user.id, db)

        return {
            "success": True,
            "data": {
                "tier": tier,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch subscription tier: {str(e)}"
        )
