from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from datetime import datetime

from db.session import get_db
from models.device_token import DeviceToken
from models.user import Profile
from schemas.device_token import DeviceTokenCreate, DeviceTokenResponse
from api.middleware.auth import require_auth
from utils.errors import log_and_raise_500

router = APIRouter(prefix="/api/device-tokens", tags=["device-tokens"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_device_token(
    token_data: DeviceTokenCreate,
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Register a device token for push notifications.
    If token already exists, update its timestamp and reactivate it.
    """
    try:
        # Check if token already exists
        existing_token = db.execute(
            select(DeviceToken).where(DeviceToken.token == token_data.token)
        ).scalar_one_or_none()

        if existing_token:
            # Token exists - update it
            existing_token.user_id = user.id
            existing_token.platform = token_data.platform
            existing_token.is_active = True
            existing_token.last_used_at = datetime.utcnow()
            existing_token.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_token)

            return {
                "success": True,
                "message": "Device token updated",
                "data": DeviceTokenResponse.model_validate(existing_token),
            }

        # Create new token
        new_token = DeviceToken(
            user_id=user.id,
            token=token_data.token,
            platform=token_data.platform,
            is_active=True,
            last_used_at=datetime.utcnow(),
        )

        db.add(new_token)
        db.commit()
        db.refresh(new_token)

        return {
            "success": True,
            "message": "Device token registered",
            "data": DeviceTokenResponse.model_validate(new_token),
        }

    except Exception as e:
        db.rollback()
        log_and_raise_500("Failed to register device token", e)


@router.delete("/{token}")
async def unregister_device_token(
    token: str,
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Unregister/deactivate a device token.
    Only the token owner can deactivate it.
    """
    try:
        # Find the token
        device_token = db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.token == token,
                    DeviceToken.user_id == user.id,
                )
            )
        ).scalar_one_or_none()

        if not device_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device token not found",
            )

        # Deactivate the token (soft delete)
        device_token.is_active = False
        device_token.updated_at = datetime.utcnow()

        db.commit()

        return {
            "success": True,
            "message": "Device token unregistered",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_and_raise_500("Failed to unregister device token", e)


@router.get("/")
async def get_device_tokens(
    user: Profile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all active device tokens for the authenticated user"""
    try:
        tokens = (
            db.execute(
                select(DeviceToken)
                .where(
                    and_(
                        DeviceToken.user_id == user.id,
                        DeviceToken.is_active == True,
                    )
                )
                .order_by(DeviceToken.created_at.desc())
            )
            .scalars()
            .all()
        )

        return {
            "success": True,
            "data": [DeviceTokenResponse.model_validate(token) for token in tokens],
        }

    except Exception as e:
        log_and_raise_500("Failed to fetch device tokens", e)
