from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List

from ...db.session import get_db
from ...models.subscription import Subscription
from ...models.user import Profile
from ...models.class_model import Class
from ...models.course import Course
from ...models.college import College
from ...schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionWithDetails,
)
from ...schemas.class_schema import ClassWithCourse
from ...schemas.course import CourseWithCollege
from ...schemas.college import CollegeResponse
from ...api.middleware.auth import require_auth

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/", response_model=List[SubscriptionWithDetails])
async def get_subscriptions(
    user: Profile = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get user's active subscriptions with details"""
    try:
        # Get user's subscriptions with class, course, and college
        query = (
            select(Subscription, Class, Course, College)
            .join(Class, Subscription.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.id)
            .join(College, Course.college_id == College.id)
            .where(
                and_(
                    Subscription.user_id == user.id,
                    Subscription.is_active == True,
                )
            )
            .order_by(Subscription.created_at.desc())
        )

        result = await db.execute(query)
        rows = result.all()

        # Build response
        subscriptions = []
        for sub, class_obj, course, college in rows:
            subscription_data = SubscriptionWithDetails(
                id=sub.id,
                college_id=sub.college_id,
                user_id=sub.user_id,
                class_id=sub.class_id,
                is_active=sub.is_active,
                last_notified=sub.last_notified,
                notification_count=sub.notification_count,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
                class_=ClassWithCourse(
                    class_id=class_obj.class_id,
                    course_id=class_obj.course_id,
                    class_number=class_obj.class_number,
                    section_code=class_obj.section_code,
                    created_at=class_obj.created_at,
                    updated_at=class_obj.updated_at,
                    is_active=class_obj.is_active,
                    current_enrollment=None,  # Not included in subscription list
                    course=CourseWithCollege(
                        id=course.id,
                        college_id=course.college_id,
                        course_code=course.course_code,
                        title=course.title,
                        created_at=course.created_at,
                        updated_at=course.updated_at,
                        is_active=course.is_active,
                        college=CollegeResponse.model_validate(college),
                    ),
                ),
            )
            subscriptions.append(subscription_data)

        return subscriptions

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch subscriptions: {str(e)}",
        )


@router.post(
    "/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    user: Profile = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new subscription"""
    try:
        # Check if subscription already exists
        existing_query = select(Subscription).where(
            and_(
                Subscription.user_id == user.id,
                Subscription.class_id == subscription_data.class_id,
                Subscription.is_active == True,
            )
        )
        existing_result = await db.execute(existing_query)
        existing_sub = existing_result.scalar_one_or_none()

        if existing_sub:
            raise HTTPException(
                status_code=409,
                detail="Already subscribed to this class",
            )

        # Verify class exists
        class_result = await db.get(Class, subscription_data.class_id)
        if not class_result:
            raise HTTPException(status_code=404, detail="Class not found")

        # Create subscription
        new_subscription = Subscription(
            college_id=subscription_data.college_id,
            user_id=user.id,
            class_id=subscription_data.class_id,
            is_active=True,
            notification_count=0,
        )

        db.add(new_subscription)
        await db.commit()
        await db.refresh(new_subscription)

        return new_subscription

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subscription: {str(e)}",
        )


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    user: Profile = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete (deactivate) a subscription"""
    try:
        # Get subscription
        subscription = await db.get(Subscription, subscription_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Verify ownership
        if subscription.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to delete this subscription",
            )

        # Deactivate instead of delete
        subscription.is_active = False
        await db.commit()

        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete subscription: {str(e)}",
        )
