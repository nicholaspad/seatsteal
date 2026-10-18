from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
import json

from db.session import get_db
from models.college import College
from models.user import Profile
from api.middleware.auth import get_optional_user
from utils.cache import CacheClient, _make_cache_key, _serialize_for_cache
from utils.college_data_status import (
    apply_data_status_map,
    get_colleges_data_status,
    overlay_data_status_on_college_dicts,
)
from utils.college_data_waitlist import (
    register_waitlist,
    waitlist_rate_limited,
)
from utils.errors import log_and_raise_500
from loguru import logger

router = APIRouter(prefix="/api/colleges", tags=["colleges"])


def _attach_data_status(db: Session, colleges):
    status_map = get_colleges_data_status(db, colleges)
    return apply_data_status_map(colleges, status_map)


def _overlay_data_status_on_payload(db: Session, payload):
    """Refresh computed dataStatus/lastUpdatedAt on a cached college payload."""
    if isinstance(payload, list):
        overlay_data_status_on_college_dicts(db, payload)
        return payload
    if isinstance(payload, dict):
        overlay_data_status_on_college_dicts(db, [payload])
    return payload


@router.get("/")
async def get_colleges(db: Session = Depends(get_db)):
    """
    Get all active colleges.

    Caching: College records cached for 1 hour; dataStatus is always computed live.
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
                response = json.loads(cached_result)
                if isinstance(response, dict) and "data" in response:
                    response["data"] = _overlay_data_status_on_payload(
                        db, response["data"]
                    )
                return response
        except Exception as e:
            logger.error(f"Cache read error: {e}")

    try:
        result = db.execute(
            select(College).where(College.is_active == True).order_by(College.name)
        )
        colleges = result.scalars().all()

        response = {
            "success": True,
            "data": _attach_data_status(db, colleges),
        }

        # Store in cache (long TTL since college data rarely changes)
        if cache_client and cache_key:
            try:
                ttl = 3600  # 1 hour
                serialized = _serialize_for_cache(response)
                cache_client.setex(cache_key, ttl, json.dumps(serialized))
                logger.debug(f"Cached colleges: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.error(f"Cache write error: {e}")

        return response

    except Exception as e:
        log_and_raise_500("Failed to fetch colleges", e)


@router.get("/{college_id}")
async def get_college(college_id: int, db: Session = Depends(get_db)):
    """
    Get college by ID.

    Caching: College record cached for 1 hour; dataStatus is always computed live.
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
                response = json.loads(cached_result)
                if isinstance(response, dict) and "data" in response:
                    response["data"] = _overlay_data_status_on_payload(
                        db, response["data"]
                    )
                return response
        except Exception as e:
            logger.error(f"Cache read error: {e}")

    college = db.get(College, college_id)
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    response = {
        "success": True,
        "data": _attach_data_status(db, [college])[0],
    }

    # Store in cache
    if cache_client and cache_key:
        try:
            ttl = 3600  # 1 hour
            serialized = _serialize_for_cache(response)
            cache_client.setex(cache_key, ttl, json.dumps(serialized))
            logger.debug(f"Cached college detail: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    return response


class DataWaitlistRequest(BaseModel):
    email: Optional[EmailStr] = None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/{college_id}/data-waitlist")
async def join_college_data_waitlist(
    college_id: int,
    request: Request,
    body: Optional[DataWaitlistRequest] = None,
    user: Optional[Profile] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Register interest when a college's seat data is unavailable.

    Auth is optional. Signed-in users are stored by user_id (and email).
    Signed-out visitors must provide a valid email. Duplicate signups
    return 200. Never deletes existing rows.
    """
    college = db.get(College, college_id)
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    client_ip = _client_ip(request)
    if waitlist_rate_limited(client_ip, college_id):
        raise HTTPException(status_code=429, detail="Too many requests")

    if user is None:
        email = body.email if body is not None else None
        if not email:
            raise HTTPException(
                status_code=422,
                detail="Email is required",
            )
        try:
            register_waitlist(db, college_id, email=str(email))
        except Exception as e:
            log_and_raise_500("Failed to join data waitlist", e)
        return {"success": True}

    try:
        register_waitlist(db, college_id, user=user)
    except Exception as e:
        log_and_raise_500("Failed to join data waitlist", e)
    return {"success": True}
