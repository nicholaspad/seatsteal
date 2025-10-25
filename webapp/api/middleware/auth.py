from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
from supabase import create_client, Client
from typing import Optional
from uuid import UUID

from config import settings
from db.session import get_db
from models.user import Profile

# HTTP Bearer token security
# auto_error=False allows optional authentication - returns None instead of 403 when no token
security = HTTPBearer(auto_error=False)

# Supabase client
supabase: Client = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Profile:
    """
    Get the current authenticated user from JWT token.

    Usage:
        @router.get("/protected")
        async def protected_route(user: Profile = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Verify JWT token with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = UUID(user_response.user.id)

        # Get user profile from database
        result = db.execute(select(Profile).where(Profile.id == user_id))
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        return profile

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[Profile]:
    """
    Get the current user if authenticated, otherwise None.

    Usage:
        @router.get("/public-or-private")
        async def route(user: Optional[Profile] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello guest"}
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_auth(user: Profile = Depends(get_current_user)) -> Profile:
    """
    Dependency to require authentication.

    Usage:
        @router.post("/subscriptions")
        async def create_subscription(
            user: Profile = Depends(require_auth)
        ):
            return {"user_id": user.id}
    """
    return user


def require_admin(user: Profile = Depends(get_current_user)) -> Profile:
    """
    Dependency to require admin authentication.

    Usage:
        @router.get("/admin/analytics")
        async def get_analytics(
            admin: Profile = Depends(require_admin)
        ):
            return {"data": "admin only"}
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
