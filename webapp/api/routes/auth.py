from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from db.session import get_db
from models.user import Profile
from models.college import College
from api.middleware.auth import require_auth
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


@router.get("/is-admin")
async def is_admin(
    user: Profile = Depends(require_auth),
):
    """Check if the current authenticated user is an admin"""
    return {
        "success": True,
        "isAdmin": user.role == "admin",
    }
