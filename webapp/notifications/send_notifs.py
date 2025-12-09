#!/usr/bin/env python3
"""
Notification job script - Sends course availability notifications to subscribed users

This script runs every minute and sends notifications based on user tier:
- Pro users: Every minute
- Plus users: Every 5 minutes
- Free users: Every 30 minutes

Usage:
    python send_notifs.py                    # Run once
    python send_notifs.py --dry-run          # Run without making DB changes
    python send_notifs.py --loop             # Run continuously every minute
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

# Add webapp directory to Python path so we can import modules
webapp_dir = Path(__file__).parent.parent
sys.path.insert(0, str(webapp_dir))

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.subscription import Subscription
from models.class_model import Class
from models.course import Course
from models.college import College
from models.enrollment import Enrollment
from models.user import Profile
from models.stripe_subscription import StripeSubscription
from models.notification_log import NotificationLog
from notifications.email_service import EmailService
from notifications.sms_service import SMSService
from notifications.constants import NOTIFICATION_CADENCE, USER_TIERS
from config import settings


class NotificationJob:
    """Handles sending notifications to users about course availability"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.email_service = EmailService()
        self.sms_service = SMSService()

    def execute(self) -> Dict:
        """
        Execute the notification job

        Returns:
            Dict with results: success, notifications_sent, duration_ms
        """
        start_time = time.time()

        try:
            if self.dry_run:
                logger.info("🧪 DRY RUN MODE - No database changes will be made")

            logger.info("🔍 Checking for notifications to send...")

            # Find notifications to send based on current minute
            with SessionLocal() as db:
                notifications = self._find_notifications_to_send(db)

                if not notifications:
                    logger.info("✅ No notifications to send")
                    return {
                        "success": True,
                        "notifications_sent": 0,
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "dry_run": self.dry_run,
                    }

                logger.info(f"📢 Found {len(notifications)} notifications to send")

                # Track tier statistics
                tier_stats = {}
                for notif in notifications:
                    tier = notif["user_tier"]
                    tier_stats[tier] = tier_stats.get(tier, 0) + 1

                logger.info(
                    f"📊 Notifications by tier: {', '.join(f'{tier}: {count}' for tier, count in tier_stats.items())}"
                )

                # Send notifications
                sent_count = 0
                failed_count = 0
                subscription_ids = []

                for notification in notifications:
                    try:
                        self._send_notification(notification, db)
                        sent_count += 1
                        subscription_ids.append(notification["subscription_id"])
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to send notification for subscription {notification['subscription_id']}: {e}"
                        )
                        failed_count += 1

                # Deactivate subscriptions (skip in dry-run mode)
                if not self.dry_run and subscription_ids:
                    self._deactivate_subscriptions(db, subscription_ids)

                # Commit all notification logs and subscription updates
                if not self.dry_run:
                    db.commit()

                if self.dry_run:
                    logger.info(
                        f"🧪 DRY RUN: Would deactivate {len(subscription_ids)} subscriptions"
                    )

                duration_ms = int((time.time() - start_time) * 1000)
                mode_text = " (DRY RUN)" if self.dry_run else ""
                logger.info(
                    f"✅ Sent {sent_count} notifications in {duration_ms}ms{mode_text}"
                )

                return {
                    "success": True,
                    "notifications_sent": sent_count,
                    "notifications_failed": failed_count,
                    "duration_ms": duration_ms,
                    "dry_run": self.dry_run,
                }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ Notification job failed: {e}")
            return {
                "success": False,
                "notifications_sent": 0,
                "error": str(e),
                "duration_ms": duration_ms,
                "dry_run": self.dry_run,
            }

    def _find_notifications_to_send(self, db: Session) -> List[Dict]:
        """
        Find all active subscriptions that should receive notifications
        Based on tier-based cadence filtering by current minute
        """
        current_minute = datetime.now().minute

        # Determine which tiers to include based on current minute
        included_tiers = []

        # Free tier: every 30 minutes (at :00 and :30)
        if current_minute % NOTIFICATION_CADENCE["FREE_TIER_MINUTES"] == 0:
            included_tiers.append(USER_TIERS["FREE"])

        # Plus tier: every 5 minutes
        if current_minute % NOTIFICATION_CADENCE["PLUS_TIER_MINUTES"] == 0:
            included_tiers.append(USER_TIERS["PLUS"])

        # Pro tier: every minute
        if current_minute % NOTIFICATION_CADENCE["PRO_TIER_MINUTES"] == 0:
            included_tiers.append(USER_TIERS["PRO"])

        logger.info(
            f"📊 Including tiers for minute :{str(current_minute).zfill(2)}: {', '.join(included_tiers)}"
        )

        if not included_tiers:
            logger.info("⚠️ No tiers included for this minute, skipping query")
            return []

        # Subquery to get the most recent enrollment for each class
        latest_enrollment_subq = (
            select(
                Enrollment.class_id,
                Enrollment.enrollment_status,
                Enrollment.scraped_at,
            )
            .where(
                and_(
                    Enrollment.enrollment_status == "open",
                )
            )
            .distinct(Enrollment.class_id)
            .order_by(Enrollment.class_id, desc(Enrollment.scraped_at))
            .subquery()
        )

        # Main query to find subscriptions that need notifications
        query = (
            select(
                Subscription.id.label("subscription_id"),
                Subscription.user_id,
                Subscription.class_id,
                Course.course_code,
                Course.title.label("course_title"),
                Class.class_number,
                Class.section_code,
                College.id.label("college_id"),
                College.name.label("college_name"),
                Profile.email.label("user_email"),
                Profile.phone.label("user_phone"),
            )
            .select_from(Subscription)
            .join(
                latest_enrollment_subq,
                Subscription.class_id == latest_enrollment_subq.c.class_id,
            )
            .join(Class, Subscription.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.id)
            .join(College, Subscription.college_id == College.id)
            .join(Profile, Subscription.user_id == Profile.id)
            .outerjoin(
                StripeSubscription,
                and_(
                    Subscription.user_id == StripeSubscription.user_id,
                    StripeSubscription.status.in_(["active", "trialing"]),
                ),
            )
            .where(
                and_(
                    Subscription.is_active == True,
                    College.is_active == True,
                    Course.is_active == True,
                    Class.is_active == True,
                )
            )
            .order_by(Subscription.created_at)
        )

        # Build tier filter - need to use case statement to add tier column
        from sqlalchemy import case, literal

        tier_column = case(
            (StripeSubscription.tier.is_(None), literal("free")),
            else_=StripeSubscription.tier,
        ).label("user_tier")

        # Add tier column to select
        query = query.add_columns(tier_column)

        # Execute query
        result = db.execute(query).all()

        # Filter by included tiers in Python (since we need the computed tier column)
        notifications = []
        for row in result:
            row_dict = row._asdict()
            if row_dict["user_tier"] in included_tiers:
                notifications.append(row_dict)

        return notifications

    def _send_notification(self, notification: Dict, db: Session) -> None:
        """Send email and SMS notifications for a course opening and log them"""
        course_code = notification["course_code"]
        course_title = notification["course_title"]
        section_code = notification["section_code"] or notification["class_number"]
        college_name = notification["college_name"]
        college_id = notification["college_id"]
        subscription_id = notification["subscription_id"]
        user_email = notification["user_email"]
        user_phone = notification.get("user_phone")
        user_tier = notification["user_tier"]

        if self.dry_run:
            logger.info(
                f"🧪 DRY RUN: Would send email to {user_email} ({user_tier}) - "
                f"{course_title} {section_code} at {college_name} is now OPEN!"
            )
            if user_phone:
                logger.info(
                    f"🧪 DRY RUN: Would send SMS to {user_phone} ({user_tier}) - "
                    f"{course_title} {section_code} at {college_name} is now OPEN!"
                )
            return

        # Build notification message for logging
        notification_message = (
            f"{course_title} ({course_code}) {section_code} at {college_name} is OPEN!"
        )

        # Send email notification
        logger.info(
            f"📧 SENDING EMAIL: To {user_email} ({user_tier}) - "
            f"{course_title} {section_code} at {college_name} is now OPEN!"
        )

        import asyncio

        # Use timeout protection to prevent blocking if email service hangs
        try:
            email_success = asyncio.run(
                asyncio.wait_for(
                    self.email_service.send_course_notification(
                        to_email=user_email,
                        course_code=course_code,
                        course_title=course_title,
                        class_section=section_code,
                        college_name=college_name,
                        unsubscribe_url=f"{settings.effective_frontend_url}/subscriptions/{notification['subscription_id']}/unsubscribe",
                    ),
                    timeout=30.0,  # 30 second timeout
                )
            )
        except asyncio.TimeoutError:
            email_success = False
            logger.error(f"⏰ EMAIL TIMEOUT: To {user_email} (exceeded 30s)")

        if email_success:
            logger.info(f"✅ EMAIL SENT: To {user_email}")
        else:
            logger.error(f"❌ EMAIL FAILED: To {user_email}")

        # Log email notification
        email_log = NotificationLog(
            college_id=college_id,
            subscription_id=subscription_id,
            user_id=notification["user_id"],
            notification_type="email",
            message=notification_message,
            status="sent" if email_success else "failed",
        )
        db.add(email_log)

        # Send SMS notification if user has phone on file
        sms_success = False
        sms_attempted = False
        if user_phone and self.sms_service.is_enabled:
            sms_attempted = True
            logger.info(
                f"📱 SENDING SMS: To {user_phone} ({user_tier}) - "
                f"{course_title} {section_code} at {college_name} is now OPEN!"
            )

            sms_success = self.sms_service.send_course_notification(
                to_phone=user_phone,
                course_name=course_title,
                section_code=section_code,
                college_name=college_name,
            )

            if sms_success:
                logger.info(f"✅ SMS SENT: To {user_phone}")
            else:
                logger.error(f"❌ SMS FAILED: To {user_phone}")

            # Log SMS notification
            sms_log = NotificationLog(
                college_id=college_id,
                subscription_id=subscription_id,
                user_id=notification["user_id"],
                notification_type="sms",
                message=notification_message,
                status="sent" if sms_success else "failed",
            )
            db.add(sms_log)

        # Consider notification successful if email succeeds (SMS is best-effort)
        if not email_success:
            raise Exception(f"Failed to send email to {user_email}")

    def _deactivate_subscriptions(
        self, db: Session, subscription_ids: List[int]
    ) -> None:
        """
        Deactivate subscriptions after notifications are sent
        Updates is_active, last_notified, and notification_count
        """
        if not subscription_ids:
            return

        # Update subscriptions in bulk
        db.query(Subscription).filter(Subscription.id.in_(subscription_ids)).update(
            {
                "is_active": False,
                "last_notified": datetime.now(),
                "notification_count": Subscription.notification_count + 1,
            },
            synchronize_session=False,
        )

        logger.info(
            f"🔄 Deactivated {len(subscription_ids)} subscriptions after sending notifications"
        )


def main():
    """Main entry point for the notification script"""
    parser = argparse.ArgumentParser(
        description="Send course availability notifications to subscribed users"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making database changes",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously every minute",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    log_level = "DEBUG" if args.debug else "INFO"
    logger.add(sys.stderr, level=log_level)

    job = NotificationJob(dry_run=args.dry_run)

    if args.loop:
        logger.info("🔁 Running in loop mode (every minute)")
        while True:
            result = job.execute()
            if not result["success"]:
                logger.error(f"Job failed: {result.get('error')}")

            # Wait until the next minute
            now = datetime.now()
            seconds_until_next_minute = 60 - now.second
            logger.info(f"⏰ Waiting {seconds_until_next_minute}s until next run...")
            time.sleep(seconds_until_next_minute)
    else:
        # Run once
        result = job.execute()
        if not result["success"]:
            logger.error(f"Job failed: {result.get('error')}")
            sys.exit(1)

        logger.info(f"✅ Job completed: {result}")


if __name__ == "__main__":
    main()
