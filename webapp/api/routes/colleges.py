from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from ...db.session import get_db
from ...models.college import College
from ...schemas.college import CollegeResponse

router = APIRouter(prefix="/api/colleges", tags=["colleges"])


@router.get("/")
async def get_colleges(db: Session = Depends(get_db)):
    """Get all active colleges"""
    try:
        result = db.execute(
            select(College).where(College.is_active == True).order_by(College.name)
        )
        colleges = result.scalars().all()

        return {
            "success": True,
            "data": [CollegeResponse.model_validate(college) for college in colleges],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch colleges: {str(e)}"
        )


@router.get("/{college_id}")
async def get_college(college_id: int, db: Session = Depends(get_db)):
    """Get college by ID"""
    college = db.get(College, college_id)
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    return {
        "success": True,
        "data": CollegeResponse.model_validate(college),
    }
