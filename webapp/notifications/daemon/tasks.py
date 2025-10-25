from celery import Celery
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
import asyncio
from datetime import datetime
from uuid import uuid4
from loguru import logger

from config import settings
from models.subscription import Subscription
from models.class_model import Class
from models.course import Course
from models.college import College
from models.enrollment import Enrollment
from notifications.email_service import EmailService

# Initialize Celery
celery_app = Celery(
    "notifications", broker=settings.REDIS_URL, backend=settings.REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=10 * 60,  # 10 minutes
    task_soft_time_limit=8 * 60,  # 8 minutes
)

# Database engine for Celery workers
engine = create_async_engine(
    settings.async_database_url,
    connect_args={
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },  # Required for pgbouncer compatibility
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="notifications.check_and_send", bind=True)
def check_and_send_notifications(self):
    """
    Check for course availability and send notifications to subscribed users.

    This task finds all active subscriptions where:
    - The class has available seats (enrolled < capacity)
    - The user hasn't been notified since the last enrollment update

    Returns:
        Dict with notification statistics
    """
    logger.info(f"[Task {self.request.id}] Starting notification check")

    async def run_notifications():
        async with AsyncSessionLocal() as db:
            email_service = EmailService()

            # Find subscriptions that need notifications
            # Join with the latest enrollment data for each class
            query = (
                select(Subscription, Class, Course, College, Enrollment)
                .join(Class, Subscription.class_id == Class.class_id)
                .join(Course, Class.course_id == Course.id)
                .join(College, Course.college_id == College.id)
                .join(
                    Enrollment,
                    and_(
                        Enrollment.class_id == Class.class_id,
                        Enrollment.recorded_at
                        == (
                            select(Enrollment.recorded_at)
                            .where(Enrollment.class_id == Class.class_id)
                            .order_by(Enrollment.recorded_at.desc())
                            .limit(1)
                            .scalar_subquery()
                        ),
                    ),
                )
                .where(
                    and_(
                        Subscription.is_active == True,
                        College.is_active == True,
                        Course.is_active == True,
                        Class.is_active == True,
                        # Available seats
                        Enrollment.enrolled < Enrollment.capacity,
                        Enrollment.capacity > 0,
                        # Not notified recently
                        (
                            Subscription.last_notified.is_(None)
                            | (Subscription.last_notified < Enrollment.recorded_at)
                        ),
                    )
                )
                .order_by(Subscription.created_at)
            )

            result = await db.execute(query)
            subscriptions_to_notify = result.all()

            logger.info(f"Found {len(subscriptions_to_notify)} subscriptions to notify")

            notifications_sent = 0
            notifications_failed = 0

            for (
                subscription,
                class_obj,
                course,
                college,
                enrollment,
            ) in subscriptions_to_notify:
                try:
                    # Calculate available spots
                    spots_available = enrollment.capacity - enrollment.enrolled

                    # Get user email from subscription
                    # Note: In a real implementation, you'd join with the Profile table
                    # For now, we'll need to fetch the user separately
                    from models.user import Profile

                    user_result = await db.execute(
                        select(Profile).where(Profile.id == subscription.user_id)
                    )
                    user = user_result.scalar_one_or_none()

                    if not user or not user.email:
                        logger.warning(
                            f"User not found for subscription {subscription.id}"
                        )
                        continue

                    # Send notification email
                    success = await email_service.send_course_notification(
                        to_email=user.email,
                        course_code=course.course_code,
                        course_title=course.title,
                        class_section=class_obj.section_code or class_obj.class_number,
                        spots_available=spots_available,
                        college_name=college.name,
                        unsubscribe_url=f"{settings.FRONTEND_URL}/subscriptions/{subscription.id}/unsubscribe",
                    )

                    if success:
                        # Update subscription
                        subscription.last_notified = enrollment.recorded_at
                        subscription.notification_count += 1
                        notifications_sent += 1

                        logger.info(
                            f"Notified {user.email} about {course.course_code} "
                            f"(subscription {subscription.id})"
                        )
                    else:
                        notifications_failed += 1

                except Exception as e:
                    logger.error(
                        f"Failed to send notification for subscription {subscription.id}: {e}"
                    )
                    notifications_failed += 1
                    continue

            # Commit all updates
            await db.commit()

            result = {
                "total_eligible": len(subscriptions_to_notify),
                "notifications_sent": notifications_sent,
                "notifications_failed": notifications_failed,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"[Task {self.request.id}] Notification check complete: "
                f"{notifications_sent} sent, {notifications_failed} failed"
            )

            return result

    try:
        return asyncio.run(run_notifications())
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Notification check failed: {e}")
        raise


@celery_app.task(name="notifications.send_single", bind=True)
def send_single_notification(
    self,
    user_email: str,
    course_code: str,
    course_title: str,
    class_section: str,
    spots_available: int,
    college_name: str,
):
    """
    Send a single notification email.

    Args:
        user_email: Recipient email
        course_code: Course code
        course_title: Course title
        class_section: Section identifier
        spots_available: Number of available spots
        college_name: College name

    Returns:
        Bool indicating success
    """
    logger.info(f"[Task {self.request.id}] Sending notification to {user_email}")

    async def send_email():
        email_service = EmailService()
        return await email_service.send_course_notification(
            to_email=user_email,
            course_code=course_code,
            course_title=course_title,
            class_section=class_section,
            spots_available=spots_available,
            college_name=college_name,
        )

    try:
        result = asyncio.run(send_email())
        logger.info(f"[Task {self.request.id}] Notification sent: {result}")
        return result
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Failed to send notification: {e}")
        raise


@celery_app.task(name="notifications.cleanup_old", bind=True)
def cleanup_old_notifications(self, days: int = 30):
    """
    Clean up old notification records (optional maintenance task).

    Args:
        days: Number of days to keep records

    Returns:
        Number of records cleaned
    """
    logger.info(
        f"[Task {self.request.id}] Cleaning up notifications older than {days} days"
    )

    async def cleanup():
        from datetime import timedelta

        async with AsyncSessionLocal() as db:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Reset old last_notified timestamps
            result = await db.execute(
                select(Subscription).where(
                    and_(
                        Subscription.last_notified < cutoff_date,
                        Subscription.is_active == True,
                    )
                )
            )

            subscriptions = result.scalars().all()
            count = len(subscriptions)

            for subscription in subscriptions:
                subscription.last_notified = None

            await db.commit()

            logger.info(f"Reset {count} old notification timestamps")
            return count

    try:
        return asyncio.run(cleanup())
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Cleanup failed: {e}")
        raise


# Health check task
@celery_app.task(name="notifications.health_check")
def health_check():
    """Simple health check task"""
    return {"status": "healthy", "service": "notifications"}
