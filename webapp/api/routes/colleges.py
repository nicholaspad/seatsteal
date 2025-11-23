from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
import json

from db.session import get_db
from models.college import College
from schemas.college import CollegeResponse
from utils.cache import CacheClient, _make_cache_key, _serialize_for_cache
from loguru import logger

router = APIRouter(prefix="/api/colleges", tags=["colleges"])


@router.get("/")
async def get_colleges(db: Session = Depends(get_db)):
    """
    Get all active colleges.

    Caching: Results cached for 30 minutes (college data rarely changes)
    """
    # Try to get from cache first
    cache_client = CacheClient.get_client()
    cache_key = None

    if cache_client:
        try:
            cache_key = _make_cache_key("colleges")
            cached_result = cache_client.get(cache_key)

            if cached_result:
                logger.debug(f"Cache hit for colleges: {cache_key}")
                return json.loads(cached_result)
        except Exception as e:
            logger.error(f"Cache read error: {e}")

    try:
        result = db.execute(
            select(College).where(College.is_active == True).order_by(College.name)
        )
        colleges = result.scalars().all()

        response = {
            "success": True,
            "data": [CollegeResponse.model_validate(college) for college in colleges],
        }

        # Store in cache (long TTL since college data rarely changes)
        if cache_client and cache_key:
            try:
                ttl = 1800  # 30 minutes
                serialized = _serialize_for_cache(response)
                cache_client.setex(cache_key, ttl, json.dumps(serialized))
                logger.debug(f"Cached colleges: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.error(f"Cache write error: {e}")

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch colleges: {str(e)}"
        )


@router.get("/{college_id}")
async def get_college(college_id: int, db: Session = Depends(get_db)):
    """
    Get college by ID.

    Caching: Results cached for 30 minutes
    """
    # Try to get from cache first
    cache_client = CacheClient.get_client()
    cache_key = None

    if cache_client:
        try:
            cache_key = _make_cache_key("college_detail", college_id=college_id)
            cached_result = cache_client.get(cache_key)

            if cached_result:
                logger.debug(f"Cache hit for college detail: {cache_key}")
                return json.loads(cached_result)
        except Exception as e:
            logger.error(f"Cache read error: {e}")

    college = db.get(College, college_id)
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    response = {
        "success": True,
        "data": CollegeResponse.model_validate(college),
    }

    # Store in cache
    if cache_client and cache_key:
        try:
            ttl = 1800  # 30 minutes
            serialized = _serialize_for_cache(response)
            cache_client.setex(cache_key, ttl, json.dumps(serialized))
            logger.debug(f"Cached college detail: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    return response
