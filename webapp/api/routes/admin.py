"""Admin API routes for analytics, user management, and platform administration"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, or_, desc, text, case
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime, timedelta
from uuid import UUID

from db.session import get_db
from models.user import Profile
from models.subscription import Subscription
from models.notification_log import NotificationLog
from models.course import Course
from models.college import College
from models.enrollment import Enrollment
from models.query_performance_metric import QueryPerformanceMetric
from models.scraper import Scraper
from models.scraper_log import ScraperLog
from models.class_model import Class
from api.middleware.auth import require_admin

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

        # Notification trends (daily counts)
        notification_trends_query = (
            select(
                func.date(NotificationLog.sent_at).label("date"),
                func.count(NotificationLog.id).label("count"),
            )
            .select_from(NotificationLog)
            .where(NotificationLog.sent_at >= days_ago)
            .group_by(func.date(NotificationLog.sent_at))
            .order_by(func.date(NotificationLog.sent_at))
        )
        notification_trends_result = db.execute(notification_trends_query)
        notification_trends = [
            {
                "date": str(row.date),
                "count": row.count,
            }
            for row in notification_trends_result
        ]

        # Recent enrollment changes
        recent_enrollment_query = (
            select(
                Class.class_id.label("classId"),
                Course.course_code.label("courseCode"),
                Course.title,
                College.name.label("collegeName"),
                Enrollment.enrollment_status.label("enrollmentStatus"),
                Enrollment.scraped_at.label("scrapedAt"),
            )
            .select_from(Enrollment)
            .join(Class, Enrollment.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.id)
            .join(College, Course.college_id == College.id)
            .where(
                and_(
                    Enrollment.scraped_at >= days_ago,
                    Course.college_id == college_id if college_id else text("1=1"),
                )
            )
            .order_by(desc(Enrollment.scraped_at))
            .limit(20)
        )
        recent_enrollment_result = db.execute(recent_enrollment_query)
        recent_enrollment_changes = [
            {
                "classId": row.classId,
                "courseCode": row.courseCode,
                "title": row.title,
                "collegeName": row.collegeName,
                "enrollmentStatus": row.enrollmentStatus,
                "scrapedAt": row.scrapedAt.isoformat() if row.scrapedAt else None,
            }
            for row in recent_enrollment_result
        ]

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
                "notificationTrends": notification_trends,
                "recentEnrollmentChanges": recent_enrollment_changes,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch analytics: {str(e)}"
        )


@router.get("/notifications")
async def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    timeframe: int = Query(30, description="Days to look back"),
    college_id: Optional[int] = Query(None, alias="college"),
    status: Optional[str] = Query(None, description="Filter by status"),
    notification_type: Optional[str] = Query(None, alias="type"),
    search: Optional[str] = Query(None, description="Search by email or course"),
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get notification logs with pagination and filtering (admin only)"""
    try:
        days_ago = datetime.utcnow() - timedelta(days=timeframe)

        # Build filters
        filters = [NotificationLog.sent_at >= days_ago]

        if college_id:
            filters.append(College.id == college_id)

        if status:
            filters.append(NotificationLog.status == status)

        if notification_type:
            filters.append(NotificationLog.notification_type == notification_type)

        # Base query with joins
        base_query = (
            select(
                NotificationLog.id,
                NotificationLog.sent_at.label("sentAt"),
                NotificationLog.notification_type.label("notificationType"),
                NotificationLog.status,
                NotificationLog.message,
                Profile.email.label("userEmail"),
                Course.course_code.label("courseCode"),
                Course.title.label("courseTitle"),
                College.name.label("collegeName"),
                NotificationLog.seats_remaining.label("seatsRemaining"),
                NotificationLog.enrollment_status.label("enrollmentStatus"),
            )
            .select_from(NotificationLog)
            .join(Subscription, NotificationLog.subscription_id == Subscription.id)
            .join(Profile, Subscription.user_id == Profile.id)
            .join(Class, Subscription.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.id)
            .join(College, Course.college_id == College.id)
            .where(and_(*filters))
        )

        # Add search filter if provided
        if search:
            search_filter = or_(
                Profile.email.ilike(f"%{search}%"),
                Course.course_code.ilike(f"%{search}%"),
                Course.title.ilike(f"%{search}%"),
            )
            base_query = base_query.where(search_filter)

        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = db.execute(count_query).scalar() or 0

        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        offset = (page - 1) * limit

        # Get paginated results
        notifications_query = (
            base_query.order_by(desc(NotificationLog.sent_at))
            .limit(limit)
            .offset(offset)
        )

        notifications_result = db.execute(notifications_query)
        notifications = [
            {
                "id": row.id,
                "sentAt": row.sentAt.isoformat() if row.sentAt else None,
                "notificationType": row.notificationType,
                "status": row.status,
                "message": row.message,
                "userEmail": row.userEmail,
                "courseCode": row.courseCode,
                "courseTitle": row.courseTitle,
                "collegeName": row.collegeName,
                "seatsRemaining": row.seatsRemaining,
                "enrollmentStatus": row.enrollmentStatus,
            }
            for row in notifications_result
        ]

        # Get colleges for filter dropdown
        colleges_query = (
            select(
                College.id.label("collegeId"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
            )
            .select_from(College)
            .order_by(College.short_name)
        )
        colleges_result = db.execute(colleges_query)
        colleges = [
            {
                "collegeId": row.collegeId,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
            }
            for row in colleges_result
        ]

        return {
            "success": True,
            "data": {
                "notifications": notifications,
                "colleges": colleges,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "totalCount": total_count,
                    "totalPages": total_pages,
                },
            },
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
        # Get total query count and slow queries (> 100ms)
        slow_threshold = 100  # milliseconds

        total_queries_result = db.execute(
            select(func.count()).select_from(QueryPerformanceMetric)
        )
        total_queries = total_queries_result.scalar() or 0

        slow_queries_result = db.execute(
            select(func.count())
            .select_from(QueryPerformanceMetric)
            .where(QueryPerformanceMetric.execution_time > slow_threshold)
        )
        slow_queries = slow_queries_result.scalar() or 0

        # Average execution time
        avg_execution_time_result = db.execute(
            select(func.avg(QueryPerformanceMetric.execution_time)).select_from(
                QueryPerformanceMetric
            )
        )
        avg_execution_time = avg_execution_time_result.scalar() or 0

        # Slow query percentage
        slow_query_percentage = (
            (slow_queries / total_queries * 100) if total_queries > 0 else 0
        )

        # Most common queries
        most_common_queries_result = db.execute(
            select(
                QueryPerformanceMetric.query_name,
                func.count(QueryPerformanceMetric.id).label("count"),
            )
            .select_from(QueryPerformanceMetric)
            .group_by(QueryPerformanceMetric.query_name)
            .order_by(desc(func.count(QueryPerformanceMetric.id)))
            .limit(10)
        )
        most_common_queries = [
            (row.query_name, row.count) for row in most_common_queries_result
        ]

        # Database connection stats (using raw SQL)
        try:
            db_stats_result = db.execute(
                text(
                    """
                SELECT
                    (SELECT count(*) FROM pg_stat_activity) as total_connections,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle') as idle_connections
                """
                )
            )
            db_stats_row = db_stats_result.first()
            database_stats = {
                "total_connections": db_stats_row.total_connections,
                "active_connections": db_stats_row.active_connections,
                "idle_connections": db_stats_row.idle_connections,
            }
        except Exception:
            # If we can't get database stats (e.g., non-PostgreSQL), return None
            database_stats = None

        # Recent slow queries
        recent_slow_queries_result = db.execute(
            select(
                QueryPerformanceMetric.query_name.label("query"),
                QueryPerformanceMetric.execution_time.label("executionTime"),
                QueryPerformanceMetric.executed_at.label("timestamp"),
                QueryPerformanceMetric.result_count.label("resultCount"),
            )
            .select_from(QueryPerformanceMetric)
            .where(QueryPerformanceMetric.execution_time > slow_threshold)
            .order_by(desc(QueryPerformanceMetric.executed_at))
            .limit(50)
        )
        recent_slow_queries = [
            {
                "query": row.query,
                "executionTime": float(row.executionTime),
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "resultCount": row.resultCount,
            }
            for row in recent_slow_queries_result
        ]

        # Hourly percentiles (P50 and P90) for the last 72 hours
        seventy_two_hours_ago = datetime.utcnow() - timedelta(hours=72)

        hourly_percentiles_query = (
            select(
                func.date_trunc("hour", QueryPerformanceMetric.executed_at).label(
                    "hour"
                ),
                func.percentile_cont(0.5)
                .within_group(QueryPerformanceMetric.execution_time)
                .label("p50"),
                func.percentile_cont(0.9)
                .within_group(QueryPerformanceMetric.execution_time)
                .label("p90"),
                func.count(QueryPerformanceMetric.id).label("queryCount"),
                func.count(QueryPerformanceMetric.id).label(
                    "totalSamples"
                ),  # Same as queryCount
            )
            .select_from(QueryPerformanceMetric)
            .where(QueryPerformanceMetric.executed_at >= seventy_two_hours_ago)
            .group_by(func.date_trunc("hour", QueryPerformanceMetric.executed_at))
            .order_by(desc(func.date_trunc("hour", QueryPerformanceMetric.executed_at)))
        )

        hourly_percentiles_result = db.execute(hourly_percentiles_query)
        hourly_percentiles = [
            {
                "hour": row.hour.isoformat() if row.hour else None,
                "p50": float(row.p50) if row.p50 else 0,
                "p90": float(row.p90) if row.p90 else 0,
                "queryCount": row.queryCount,
                "totalSamples": row.totalSamples,
            }
            for row in hourly_percentiles_result
        ]

        return {
            "success": True,
            "data": {
                "stats": {
                    "totalQueries": total_queries,
                    "slowQueries": slow_queries,
                    "avgExecutionTime": round(avg_execution_time, 2),
                    "slowQueryPercentage": round(slow_query_percentage, 2),
                    "mostCommonQueries": most_common_queries,
                },
                "databaseStats": database_stats,
                "recentSlowQueries": recent_slow_queries,
                "hourlyPercentiles": hourly_percentiles,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch query performance: {str(e)}"
        )


@router.get("/scrapers")
async def get_scrapers(
    timeframe: int = Query(30, description="Days to look back"),
    college_id: Optional[int] = Query(None, alias="college"),
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get scraper analytics (admin only)"""
    try:
        days_ago = datetime.utcnow() - timedelta(days=timeframe)

        # Build college filter
        college_filter = Scraper.college_id == college_id if college_id else text("1=1")

        # Overview statistics
        total_scrapers = db.execute(
            select(func.count()).select_from(Scraper).where(college_filter)
        ).scalar()

        active_scrapers = db.execute(
            select(func.count())
            .select_from(Scraper)
            .where(and_(Scraper.status == "running", college_filter))
        ).scalar()

        error_scrapers = db.execute(
            select(func.count())
            .select_from(Scraper)
            .where(and_(Scraper.status == "error", college_filter))
        ).scalar()

        # Recent run statistics
        recent_runs_result = db.execute(
            select(
                func.count().label("totalRuns"),
                func.sum(case((ScraperLog.outcome == "success", 1), else_=0)).label(
                    "successfulRuns"
                ),
                func.avg(ScraperLog.duration_ms).label("avgDuration"),
            )
            .select_from(ScraperLog)
            .join(Scraper, ScraperLog.scraper_id == Scraper.id)
            .where(and_(ScraperLog.started_at >= days_ago, college_filter))
        )
        recent_stats = recent_runs_result.first()
        total_runs = recent_stats.totalRuns or 0
        successful_runs = recent_stats.successfulRuns or 0
        avg_duration = recent_stats.avgDuration or 0
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

        recent_errors = db.execute(
            select(func.count())
            .select_from(ScraperLog)
            .join(Scraper, ScraperLog.scraper_id == Scraper.id)
            .where(
                and_(
                    ScraperLog.outcome == "error",
                    ScraperLog.started_at >= days_ago,
                    college_filter,
                )
            )
        ).scalar()

        # Scraper details
        scrapers_details_query = (
            select(
                Scraper.id.label("scraperId"),
                Scraper.status,
                Scraper.college_id.label("collegeId"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
                Scraper.last_run_at.label("lastRunAt"),
                Scraper.last_success_at.label("lastSuccessAt"),
                Scraper.next_run_at.label("nextRunAt"),
                Scraper.run_count.label("runCount"),
                Scraper.success_count.label("successCount"),
                Scraper.error_count.label("errorCount"),
                Scraper.last_error_message.label("lastErrorMessage"),
                Scraper.last_run_duration_ms.label("lastRunDurationMs"),
                Scraper.created_at.label("createdAt"),
                Scraper.updated_at.label("updatedAt"),
            )
            .select_from(Scraper)
            .join(College, Scraper.college_id == College.id)
            .where(college_filter)
            .order_by(College.short_name)
        )
        scrapers_details_result = db.execute(scrapers_details_query)
        scraper_details = [
            {
                "scraperId": row.scraperId,
                "status": row.status,
                "collegeId": row.collegeId,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
                "lastRunAt": row.lastRunAt.isoformat() if row.lastRunAt else None,
                "lastSuccessAt": (
                    row.lastSuccessAt.isoformat() if row.lastSuccessAt else None
                ),
                "nextRunAt": row.nextRunAt.isoformat() if row.nextRunAt else None,
                "runCount": row.runCount or 0,
                "successCount": row.successCount or 0,
                "errorCount": row.errorCount or 0,
                "lastErrorMessage": row.lastErrorMessage,
                "lastRunDurationMs": row.lastRunDurationMs,
                "createdAt": row.createdAt.isoformat() if row.createdAt else None,
                "updatedAt": row.updatedAt.isoformat() if row.updatedAt else None,
            }
            for row in scrapers_details_result
        ]

        # Success rate trends by date and college
        success_rate_trends_query = (
            select(
                func.date(ScraperLog.started_at).label("date"),
                Scraper.college_id.label("collegeId"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
                func.count(ScraperLog.id).label("totalRuns"),
                func.sum(case((ScraperLog.outcome == "success", 1), else_=0)).label(
                    "successfulRuns"
                ),
            )
            .select_from(ScraperLog)
            .join(Scraper, ScraperLog.scraper_id == Scraper.id)
            .join(College, Scraper.college_id == College.id)
            .where(and_(ScraperLog.started_at >= days_ago, college_filter))
            .group_by(
                func.date(ScraperLog.started_at),
                Scraper.college_id,
                College.name,
                College.short_name,
            )
            .order_by(func.date(ScraperLog.started_at))
        )
        success_rate_trends_result = db.execute(success_rate_trends_query)
        success_rate_trends = [
            {
                "date": str(row.date),
                "collegeId": row.collegeId,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
                "totalRuns": row.totalRuns,
                "successfulRuns": row.successfulRuns,
                "successRate": (
                    (row.successfulRuns / row.totalRuns * 100)
                    if row.totalRuns > 0
                    else 0
                ),
            }
            for row in success_rate_trends_result
        ]

        # Performance trends (avg duration by date/college)
        performance_trends_query = (
            select(
                func.date(ScraperLog.started_at).label("date"),
                Scraper.college_id.label("collegeId"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
                func.avg(ScraperLog.duration_ms).label("avgDuration"),
                func.sum(case((ScraperLog.outcome == "success", 1), else_=0)).label(
                    "successCount"
                ),
                func.sum(case((ScraperLog.outcome == "error", 1), else_=0)).label(
                    "errorCount"
                ),
                func.count(ScraperLog.id).label("totalRuns"),
            )
            .select_from(ScraperLog)
            .join(Scraper, ScraperLog.scraper_id == Scraper.id)
            .join(College, Scraper.college_id == College.id)
            .where(
                and_(
                    ScraperLog.started_at >= days_ago,
                    ScraperLog.duration_ms.isnot(None),
                    college_filter,
                )
            )
            .group_by(
                func.date(ScraperLog.started_at),
                Scraper.college_id,
                College.name,
                College.short_name,
            )
            .order_by(func.date(ScraperLog.started_at))
        )
        performance_trends_result = db.execute(performance_trends_query)
        performance_trends = [
            {
                "date": str(row.date),
                "collegeId": row.collegeId,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
                "avgDuration": float(row.avgDuration) if row.avgDuration else 0,
                "successCount": row.successCount,
                "errorCount": row.errorCount,
                "totalRuns": row.totalRuns,
            }
            for row in performance_trends_result
        ]

        # Recent activity
        recent_activity_query = (
            select(
                ScraperLog.id.label("logId"),
                ScraperLog.scraper_id.label("scraperId"),
                ScraperLog.outcome,
                ScraperLog.started_at.label("startedAt"),
                ScraperLog.completed_at.label("completedAt"),
                ScraperLog.duration_ms.label("durationMs"),
                ScraperLog.error_message.label("errorMessage"),
                ScraperLog.courses_created.label("coursesCreated"),
                ScraperLog.classes_created.label("classesCreated"),
                ScraperLog.enrollments_saved.label("enrollmentsSaved"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
            )
            .select_from(ScraperLog)
            .join(Scraper, ScraperLog.scraper_id == Scraper.id)
            .join(College, Scraper.college_id == College.id)
            .where(college_filter)
            .order_by(desc(ScraperLog.started_at))
            .limit(50)
        )
        recent_activity_result = db.execute(recent_activity_query)
        recent_activity = [
            {
                "logId": row.logId,
                "scraperId": row.scraperId,
                "outcome": row.outcome,
                "startedAt": row.startedAt.isoformat() if row.startedAt else None,
                "completedAt": (
                    row.completedAt.isoformat() if row.completedAt else None
                ),
                "durationMs": row.durationMs,
                "errorMessage": row.errorMessage,
                "coursesCreated": row.coursesCreated or 0,
                "classesCreated": row.classesCreated or 0,
                "enrollmentsSaved": row.enrollmentsSaved or 0,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
            }
            for row in recent_activity_result
        ]

        # Recent errors
        recent_errors_query = (
            select(
                ScraperLog.id.label("logId"),
                ScraperLog.scraper_id.label("scraperId"),
                ScraperLog.started_at.label("startedAt"),
                ScraperLog.error_message.label("errorMessage"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
            )
            .select_from(ScraperLog)
            .join(Scraper, ScraperLog.scraper_id == Scraper.id)
            .join(College, Scraper.college_id == College.id)
            .where(and_(ScraperLog.outcome == "error", college_filter))
            .order_by(desc(ScraperLog.started_at))
            .limit(20)
        )
        recent_errors_result = db.execute(recent_errors_query)
        recent_error_details = [
            {
                "logId": row.logId,
                "scraperId": row.scraperId,
                "startedAt": row.startedAt.isoformat() if row.startedAt else None,
                "errorMessage": row.errorMessage,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
            }
            for row in recent_errors_result
        ]

        # College stats
        college_stats_query = (
            select(
                College.id.label("collegeId"),
                College.name.label("collegeName"),
                College.short_name.label("shortName"),
                func.count(Scraper.id).label("scraperCount"),
            )
            .select_from(College)
            .outerjoin(Scraper, College.id == Scraper.college_id)
            .group_by(College.id, College.name, College.short_name)
            .order_by(College.short_name)
        )
        college_stats_result = db.execute(college_stats_query)
        college_stats = [
            {
                "collegeId": row.collegeId,
                "collegeName": row.collegeName,
                "shortName": row.shortName,
                "scraperCount": row.scraperCount,
            }
            for row in college_stats_result
        ]

        return {
            "success": True,
            "data": {
                "overview": {
                    "totalScrapers": total_scrapers,
                    "activeScrapers": active_scrapers,
                    "errorScrapers": error_scrapers,
                    "successRate": round(success_rate, 2),
                    "avgDuration": round(avg_duration, 2) if avg_duration else 0,
                    "recentErrors": recent_errors,
                    "totalRuns": total_runs,
                    "successfulRuns": successful_runs,
                },
                "scraperDetails": scraper_details,
                "successRateTrends": success_rate_trends,
                "performanceTrends": performance_trends,
                "recentActivity": recent_activity,
                "recentErrorDetails": recent_error_details,
                "collegeStats": college_stats,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch scrapers: {str(e)}"
        )


@router.get("/users")
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get users with pagination and filtering (admin only)"""
    try:
        # Build filters
        filters = []

        if search:
            filters.append(Profile.email.ilike(f"%{search}%"))

        if role:
            filters.append(Profile.role == role)

        # Count total
        count_query = select(func.count()).select_from(Profile)
        if filters:
            count_query = count_query.where(and_(*filters))
        total_count = db.execute(count_query).scalar() or 0

        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        offset = (page - 1) * limit

        # Get users with college data
        users_query = (
            select(
                Profile.id,
                Profile.email,
                Profile.phone,
                Profile.role,
                Profile.college_id.label("collegeId"),
                College.id.label("college_id_inner"),
                College.name.label("college_name"),
                College.short_name.label("college_short_name"),
            )
            .select_from(Profile)
            .outerjoin(College, Profile.college_id == College.id)
        )

        if filters:
            users_query = users_query.where(and_(*filters))

        users_query = users_query.order_by(desc(Profile.id)).limit(limit).offset(offset)

        users_result = db.execute(users_query)
        users = [
            {
                "id": str(row.id),
                "email": row.email,
                "phone": row.phone,
                "role": row.role,
                "collegeId": row.collegeId,
                "college": (
                    {
                        "id": row.college_id_inner,
                        "name": row.college_name,
                        "shortName": row.college_short_name,
                    }
                    if row.college_id_inner
                    else None
                ),
            }
            for row in users_result
        ]

        return {
            "success": True,
            "data": {
                "users": users,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "totalCount": total_count,
                    "totalPages": total_pages,
                },
            },
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
