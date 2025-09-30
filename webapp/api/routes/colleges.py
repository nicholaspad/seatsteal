from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ...db.session import get_db
from ...models.college import College
from ...schemas.college import CollegeResponse

router = APIRouter(prefix="/api/colleges", tags=["colleges"])


@router.get("/", response_model=List[CollegeResponse])
async def get_colleges(db: AsyncSession = Depends(get_db)):
    """Get all active colleges"""
    try:
        result = await db.execute(
            select(College).where(College.is_active == True).order_by(College.name)
        )
        colleges = result.scalars().all()
        return colleges
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch colleges: {str(e)}")


@router.get("/{college_id}", response_model=CollegeResponse)
async def get_college(college_id: int, db: AsyncSession = Depends(get_db)):
    """Get college by ID"""
    college = await db.get(College, college_id)
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college