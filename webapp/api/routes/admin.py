"""Admin API routes for analytics, user management, and platform administration"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, or_, desc, text
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime, timedelta
from uuid import UUID

from ...db.session import get_db
from ...models.user import Profile
from ...models.subscription import Subscription
from ...models.notification_log import NotificationLog
from ...models.course import Course
from ...models.college import College
from ...models.enrollment import Enrollment
from ...models.query_performance_metric import QueryPerformanceMetric
from ...models.scraper import Scraper
from ...models.scraper_log import ScraperLog
from ...api.middleware.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/analytics")
async def get_analytics(
    timeframe: int = Query(30, description="Days to look back"),
    college_id: Optional[int] = Query(None, alias="college"),
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get platform analytics (admin only)"""
    try:
        days_ago = datetime.utcnow() - timedelta(days=timeframe)

        # Build college filter
        college_filter = College.id == college_id if college_id else text("1=1")

        # User statistics
        total_users_result = db.execute(
            select(func.count())
            .select_from(Profile)
            .where(Profile.college_id == college_id if college_id else text("1=1"))
        )
        total_users = total_users_result.scalar() or 0

        admin_users_result = db.execute(
            select(func.count())
            .select_from(Profile)
            .where(
                and_(
                    Profile.role == "admin",
                    Profile.college_id == college_id if college_id else text("1=1"),
                )
            )
        )
        admin_users = admin_users_result.scalar() or 0

        # Subscription statistics
        total_subs_result = db.execute(select(func.count()).select_from(Subscription))
        total_subscriptions = total_subs_result.scalar() or 0

        active_subs_result = db.execute(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.is_active == True)
        )
        active_subscriptions = active_subs_result.scalar() or 0

        recent_subs_result = db.execute(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.created_at >= days_ago)
        )
        recent_subscriptions = recent_subs_result.scalar() or 0

        # Notification statistics
        total_notifs_result = db.execute(
            select(func.count()).select_from(NotificationLog)
        )
        total_notifications = total_notifs_result.scalar() or 0

        recent_notifs_result = db.execute(
            select(func.count())
            .select_from(NotificationLog)
            .where(NotificationLog.sent_at >= days_ago)
        )
        recent_notifications = recent_notifs_result.scalar() or 0

        successful_notifs_result = db.execute(
            select(func.count())
            .select_from(NotificationLog)
            .where(NotificationLog.status == "sent")
        )
        successful_notifications = successful_notifs_result.scalar() or 0

        failed_notifs_result = db.execute(
            select(func.count())
            .select_from(NotificationLog)
            .where(NotificationLog.status == "failed")
        )
        failed_notifications = failed_notifs_result.scalar() or 0

        # Course and college counts
        total_courses_result = db.execute(
            select(func.count())
            .select_from(Course)
            .where(Course.college_id == college_id if college_id else text("1=1"))
        )
        total_courses = total_courses_result.scalar() or 0

        total_colleges_result = db.execute(select(func.count()).select_from(College))
        total_colleges = total_colleges_result.scalar() or 0

        # Most popular courses
        popular_courses_query = (
            select(
                Course.id.label("courseId"),
                Course.course_code.label("courseCode"),
                Course.title,
                College.name.label("collegeName"),
                func.count(Subscription.id).label("subscriptionCount"),
            )
            .select_from(Course)
            .outerjoin(Subscription, Course.id == Subscription.class_id)
            .outerjoin(College, Course.college_id == College.id)
            .where(Course.college_id == college_id if college_id else text("1=1"))
            .group_by(Course.id, Course.course_code, Course.title, College.name)
            .order_by(desc(func.count(Subscription.id)))
            .limit(10)
        )
        popular_courses_result = db.execute(popular_courses_query)
        popular_courses = [
            {
                "courseId": row.courseId,
                "courseCode": row.courseCode,
                "title": row.title,
                "collegeName": row.collegeName,
                "subscriptionCount": row.subscriptionCount,
            }
            for row in popular_courses_result
        ]

        # College usage statistics
        college_stats_query = (
            select(
                College.id.label("collegeId"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
                func.count(Profile.id).label("userCount"),
            )
            .select_from(College)
            .outerjoin(Profile, College.id == Profile.college_id)
            .group_by(College.id, College.name, College.short_name)
            .order_by(desc(func.count(Profile.id)))
        )
        college_stats_result = db.execute(college_stats_query)
        college_stats = [
            {
                "collegeId": row.collegeId,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
                "userCount": row.userCount,
            }
            for row in college_stats_result
        ]

        # Calculate notification success rate
        notification_success_rate = (
            (successful_notifications / total_notifications * 100)
            if total_notifications > 0
            else 0
        )

        return {
            "success": True,
            "data": {
                "overview": {
                    "totalUsers": total_users,
                    "adminUsers": admin_users,
                    "newUsers": total_users,  # Placeholder - would need created_at on Profile
                    "totalSubscriptions": total_subscriptions,
                    "activeSubscriptions": active_subscriptions,
                    "recentSubscriptions": recent_subscriptions,
                    "totalNotifications": total_notifications,
                    "recentNotifications": recent_notifications,
                    "successfulNotifications": successful_notifications,
                    "failedNotifications": failed_notifications,
                    "totalCourses": total_courses,
                    "totalColleges": total_colleges,
                    "notificationSuccessRate": round(notification_success_rate, 2),
                },
                "popularCourses": popular_courses,
                "collegeStats": college_stats,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch analytics: {str(e)}"
        )


@router.get("/notifications")
async def get_notifications(
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get notification logs (admin only)"""
    try:
        result = db.execute(
            select(NotificationLog).order_by(desc(NotificationLog.sent_at)).limit(100)
        )
        logs = result.scalars().all()

        return {
            "success": True,
            "data": [
                {
                    "id": log.id,
                    "subscriptionId": log.subscription_id,
                    "collegeId": log.college_id,
                    "notificationType": log.notification_type,
                    "message": log.message,
                    "status": log.status,
                    "sentAt": log.sent_at.isoformat() if log.sent_at else None,
                }
                for log in logs
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch notifications: {str(e)}"
        )


@router.get("/query-performance")
async def get_query_performance(
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get query performance metrics (admin only)"""
    try:
        result = db.execute(
            select(QueryPerformanceMetric)
            .order_by(desc(QueryPerformanceMetric.executed_at))
            .limit(100)
        )
        metrics = result.scalars().all()

        return {
            "success": True,
            "data": [
                {
                    "id": metric.id,
                    "queryName": metric.query_name,
                    "executionTime": metric.execution_time,
                    "executedAt": (
                        metric.executed_at.isoformat() if metric.executed_at else None
                    ),
                }
                for metric in metrics
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch query performance: {str(e)}"
        )


@router.get("/scrapers")
async def get_scrapers(
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get scraper status and logs (admin only)"""
    try:
        # Get all scrapers with latest log
        scrapers_query = select(Scraper).options()
        scrapers_result = db.execute(scrapers_query)
        scrapers = scrapers_result.scalars().all()

        scrapers_data = []
        for scraper in scrapers:
            # Get latest log
            log_result = db.execute(
                select(ScraperLog)
                .where(ScraperLog.scraper_id == scraper.id)
                .order_by(desc(ScraperLog.started_at))
                .limit(1)
            )
            latest_log = log_result.scalar_one_or_none()

            scrapers_data.append(
                {
                    "id": scraper.id,
                    "collegeId": scraper.college_id,
                    "status": scraper.status,
                    "latestLog": (
                        {
                            "id": latest_log.id,
                            "outcome": latest_log.outcome,
                            "startedAt": (
                                latest_log.started_at.isoformat()
                                if latest_log.started_at
                                else None
                            ),
                            "completedAt": (
                                latest_log.completed_at.isoformat()
                                if latest_log.completed_at
                                else None
                            ),
                            "errorMessage": latest_log.error_message,
                        }
                        if latest_log
                        else None
                    ),
                }
            )

        return {
            "success": True,
            "data": scrapers_data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch scrapers: {str(e)}"
        )


@router.get("/users")
async def get_users(
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get all users (admin only)"""
    try:
        result = db.execute(select(Profile).order_by(desc(Profile.id)).limit(100))
        users = result.scalars().all()

        return {
            "success": True,
            "data": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "collegeId": user.college_id,
                }
                for user in users
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get specific user details (admin only)"""
    try:
        result = db.execute(select(Profile).where(Profile.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "success": True,
            "data": {
                "id": str(user.id),
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "collegeId": user.college_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")


class UpdateUserRequest(BaseModel):
    """Request schema for updating user"""

    role: Optional[Literal["user", "admin"]] = None
    college_id: Optional[int] = Field(None, alias="collegeId")

    model_config = ConfigDict(populate_by_name=True)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user details (admin only)"""
    try:
        result = db.execute(select(Profile).where(Profile.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update fields
        if request.role is not None:
            user.role = request.role
        if request.college_id is not None:
            user.college_id = request.college_id

        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "data": {
                "id": str(user.id),
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "collegeId": user.college_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")
