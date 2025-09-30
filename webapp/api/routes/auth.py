from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...db.session import get_db
from ...models.user import Profile
from ...models.college import College
from ...api.middleware.auth import require_auth

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