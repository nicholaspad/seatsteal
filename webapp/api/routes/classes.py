from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import json

from db.session import get_db
from utils.cache import CacheClient, _make_cache_key, _serialize_for_cache
from loguru import logger
from models.class_model import Class
from models.course import Course
from models.college import College
from models.enrollment import Enrollment
from models.subscription import Subscription
from models.notification_log import NotificationLog
from schemas.class_schema import ClassWithCourse
from schemas.course import EnrollmentStatus, CourseWithCollege
from schemas.college import CollegeResponse
from api.middleware.auth import require_auth
from utils.premium import require_premium_access
from utils.errors import log_and_raise_500

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("/{class_id}")
async def get_class(class_id: int, db: Session = Depends(get_db)):
    """
    Get class details with course, college, and latest enrollment.

    Caching: Results cached for 5 minutes
    """
    # Try to get from cache first
    cache_client = CacheClient.get_client()
    cache_key = None

    if cache_client:
        try:
            cache_key = _make_cache_key("class_detail", class_id=class_id)
            cached_result = cache_client.get(cache_key)

            if cached_result:
                logger.debug(f"Cache hit for class detail: {cache_key}")
                return json.loads(cached_result)
        except Exception as e:
            logger.error(f"Cache read error: {e}")

    try:
        # Get class with related course and college
        class_query = (
            select(Class, Course, College)
            .join(Course, Class.course_id == Course.id)
            .join(College, Course.college_id == College.id)
            .where(and_(Class.class_id == class_id, Class.is_active == True))
        )
        result = db.execute(class_query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Class not found")

        class_obj, course, college = row

        # Get latest enrollment
        enrollment_query = (
            select(Enrollment)
            .where(Enrollment.class_id == class_id)
            .order_by(Enrollment.scraped_at.desc())
            .limit(1)
        )
        enrollment_result = db.execute(enrollment_query)
        enrollment = enrollment_result.scalar_one_or_none()

        # Build response
        class_data = ClassWithCourse(
            class_id=class_obj.class_id,
            course_id=class_obj.course_id,
            class_number=class_obj.class_number,
            section_code=class_obj.section_code,
            created_at=class_obj.created_at,
            updated_at=class_obj.updated_at,
            is_active=class_obj.is_active,
            current_enrollment=(
                EnrollmentStatus(
                    enrollment_status=enrollment.enrollment_status,
                    scraped_at=enrollment.scraped_at.isoformat(),
                )
                if enrollment
                else None
            ),
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
        )

        response = {
            "success": True,
            "data": class_data,
        }

        # Store in cache (shorter TTL since enrollment data changes frequently)
        if cache_client and cache_key:
            try:
                ttl = 300  # 5 minutes
                serialized = _serialize_for_cache(response)
                cache_client.setex(cache_key, ttl, json.dumps(serialized))
                logger.debug(f"Cached class detail: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.error(f"Cache write error: {e}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_500("Failed to fetch class details", e)


@router.get("/{class_id}/enrollment-analysis")
async def get_enrollment_analysis(
    class_id: int,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get enrollment analysis for a class (Premium feature)"""
    try:
        # Require premium access
        require_premium_access(user.id, db)

        # Get times opened in last 60 days
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        times_opened_query = text(
            """
            WITH status_changes AS (
                SELECT
                    scraped_at,
                    enrollment_status,
                    LAG(enrollment_status) OVER (ORDER BY scraped_at) as prev_status
                FROM enrollments
                WHERE class_id = :class_id
                  AND scraped_at > :sixty_days_ago
                  AND enrollment_status IS NOT NULL
                ORDER BY scraped_at
            )
            SELECT COUNT(*) as times_opened
            FROM status_changes
            WHERE enrollment_status = 'open'
              AND (prev_status = 'closed' OR prev_status IS NULL)
            """
        )
        times_result = db.execute(
            times_opened_query, {"class_id": class_id, "sixty_days_ago": sixty_days_ago}
        )
        times_opened_last_60_days = times_result.scalar() or 0

        # Get average days to open
        avg_days_query = text(
            """
            WITH closed_to_open_transitions AS (
                SELECT
                    e1.scraped_at as closed_time,
                    (
                        SELECT MIN(e2.scraped_at)
                        FROM enrollments e2
                        WHERE e2.class_id = :class_id
                          AND e2.scraped_at > e1.scraped_at
                          AND e2.enrollment_status = 'open'
                    ) as next_open_time
                FROM enrollments e1
                WHERE e1.class_id = :class_id
                  AND e1.scraped_at > :sixty_days_ago
                  AND e1.enrollment_status = 'closed'
            )
            SELECT AVG(
                EXTRACT(EPOCH FROM (next_open_time - closed_time)) / 86400
            ) as avg_days_to_open
            FROM closed_to_open_transitions
            WHERE next_open_time IS NOT NULL
            """
        )
        avg_result = db.execute(
            avg_days_query, {"class_id": class_id, "sixty_days_ago": sixty_days_ago}
        )
        avg_days_to_open_last_60_days = round(avg_result.scalar() or 0, 1)

        # Get most recent opening
        most_recent_query = text(
            """
            SELECT MAX(scraped_at) as most_recent_opening
            FROM enrollments e1
            WHERE e1.class_id = :class_id
              AND e1.enrollment_status = 'open'
              AND EXISTS (
                  SELECT 1 FROM enrollments e2
                  WHERE e2.class_id = e1.class_id
                    AND e2.scraped_at < e1.scraped_at
                    AND e2.scraped_at > e1.scraped_at - INTERVAL '2 days'
                    AND e2.enrollment_status = 'closed'
              )
            """
        )
        recent_result = db.execute(most_recent_query, {"class_id": class_id})
        most_recent_opening = recent_result.scalar()

        # Fallback to most recent open status if no transition found
        if not most_recent_opening:
            fallback_query = (
                select(Enrollment.scraped_at)
                .where(
                    and_(
                        Enrollment.class_id == class_id,
                        Enrollment.enrollment_status == "open",
                    )
                )
                .order_by(Enrollment.scraped_at.desc())
                .limit(1)
            )
            fallback_result = db.execute(fallback_query)
            most_recent_opening = fallback_result.scalar()

        # Get subscription statistics
        subs_count_result = db.execute(
            select(func.count())
            .select_from(Subscription)
            .where(
                and_(Subscription.class_id == class_id, Subscription.is_active == True)
            )
        )
        subscriptions_count = subs_count_result.scalar() or 0

        # Get notifications sent
        notifs_count_result = db.execute(
            select(func.count())
            .select_from(NotificationLog)
            .join(Subscription, NotificationLog.subscription_id == Subscription.id)
            .where(
                and_(
                    Subscription.class_id == class_id, NotificationLog.status == "sent"
                )
            )
        )
        notifications_sent = notifs_count_result.scalar() or 0

        # Get recent notifications (last 14 days)
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
        recent_notifs_result = db.execute(
            select(func.count())
            .select_from(NotificationLog)
            .join(Subscription, NotificationLog.subscription_id == Subscription.id)
            .where(
                and_(
                    Subscription.class_id == class_id,
                    NotificationLog.status == "sent",
                    NotificationLog.sent_at > fourteen_days_ago,
                )
            )
        )
        recent_notifications = recent_notifs_result.scalar() or 0

        # Calculate competition level
        competition_score = subscriptions_count * 2 + recent_notifications
        if avg_days_to_open_last_60_days > 0:
            competition_score += max(0, 10 - avg_days_to_open_last_60_days)

        if competition_score <= 10:
            competition_level = "low"
        elif competition_score <= 25:
            competition_level = "medium"
        else:
            competition_level = "high"

        return {
            "success": True,
            "data": {
                "classId": class_id,
                "timesOpenedLast60Days": times_opened_last_60_days,
                "avgDaysToOpenLast60Days": avg_days_to_open_last_60_days,
                "mostRecentOpening": (
                    most_recent_opening.isoformat() if most_recent_opening else None
                ),
                "subscriptionsCount": subscriptions_count,
                "notificationsSent": notifications_sent,
                "competitionLevel": competition_level,
                "generatedAt": datetime.utcnow().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_500("Failed to fetch enrollment analysis", e)
