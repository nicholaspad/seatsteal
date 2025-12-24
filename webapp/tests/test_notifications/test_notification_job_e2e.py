"""
End-to-end integration tests for notification job.

These tests verify the complete notification workflow:
1. Setup course/class/enrollment/subscription data with different user tiers
2. Simulate scraper job changing enrollment from closed to open
3. Run notifications job and verify correct users are notified based on minute
4. Verify users get unsubscribed after notification
"""

import pytest
from freezegun import freeze_time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from notifications.send_notifs import NotificationJob
from models.subscription import Subscription
from models.enrollment import Enrollment
from models.stripe_subscription import StripeSubscription
from models.stripe_customer import StripeCustomer
from models.notification_log import NotificationLog
from models.user import Profile
from models.college import College
from models.course import Course
from models.class_model import Class


@pytest.fixture
def free_user(test_db: Session, test_college: College) -> Profile:
    """Create a free tier user (no Stripe subscription)."""
    user = Profile(
        id=str(uuid4()),
        email="free@test.edu",
        phone="+11234567890",
        college_id=test_college.id,
        role="user",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def plus_user(test_db: Session, test_college: College) -> Profile:
    """Create a plus tier user with active Stripe subscription."""
    user = Profile(
        id=str(uuid4()),
        email="plus@test.edu",
        phone="+11234567891",
        college_id=test_college.id,
        role="user",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Create Stripe customer
    customer = StripeCustomer(
        user_id=user.id,
        stripe_customer_id="cus_plus_e2e",
        email=user.email,
    )
    test_db.add(customer)

    # Create Plus Stripe subscription
    stripe_sub = StripeSubscription(
        user_id=user.id,
        stripe_subscription_id="sub_plus_e2e",
        stripe_customer_id="cus_plus_e2e",
        price_id="price_plus",
        tier="plus",
        status="active",
    )
    test_db.add(stripe_sub)
    test_db.commit()

    return user


@pytest.fixture
def pro_user(test_db: Session, test_college: College) -> Profile:
    """Create a pro tier user with active Stripe subscription."""
    user = Profile(
        id=str(uuid4()),
        email="pro@test.edu",
        phone="+11234567892",
        college_id=test_college.id,
        role="user",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Create Stripe customer
    customer = StripeCustomer(
        user_id=user.id,
        stripe_customer_id="cus_pro_e2e",
        email=user.email,
    )
    test_db.add(customer)

    # Create Pro Stripe subscription
    stripe_sub = StripeSubscription(
        user_id=user.id,
        stripe_subscription_id="sub_pro_e2e",
        stripe_customer_id="cus_pro_e2e",
        price_id="price_pro",
        tier="pro",
        status="active",
    )
    test_db.add(stripe_sub)
    test_db.commit()

    return user


@pytest.fixture
def mock_email_service_e2e():
    """Mock email service for E2E tests."""
    with patch("notifications.send_notifs.EmailService") as mock_class:
        mock_service = MagicMock()
        mock_service.send_course_notification = AsyncMock(return_value=True)
        mock_class.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_sms_service_e2e():
    """Mock SMS service for E2E tests."""
    with patch("notifications.send_notifs.SMSService") as mock_class:
        mock_service = MagicMock()
        mock_service.is_enabled = False
        mock_service.send_course_notification.return_value = True
        mock_class.return_value = mock_service
        yield mock_service


class TestNotificationJobE2E:
    """End-to-end integration tests for the complete notification workflow."""

    @pytest.mark.integration
    @freeze_time("2024-01-15 10:00:00")
    def test_all_tiers_notified_on_minute_00(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_class: Class,
        free_user: Profile,
        plus_user: Profile,
        pro_user: Profile,
        mock_email_service_e2e,
        mock_sms_service_e2e,
    ):
        """
        Test complete workflow: all tiers get notified when minute is :00.

        Workflow:
        1. Create subscriptions for free, plus, and pro users
        2. Simulate scraper: enrollment changes from closed to open
        3. Run notification job at minute :00
        4. Verify all 3 users are notified and unsubscribed
        """
        # Step 1: Create subscriptions for all users
        free_sub = Subscription(
            user_id=free_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
            notification_count=0,
        )
        plus_sub = Subscription(
            user_id=plus_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
            notification_count=0,
        )
        pro_sub = Subscription(
            user_id=pro_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
            notification_count=0,
        )
        test_db.add_all([free_sub, plus_sub, pro_sub])
        test_db.commit()

        # Step 2: Simulate scraper - create closed enrollment first
        closed_enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="closed",
            scraped_at=datetime(2024, 1, 15, 9, 55, tzinfo=timezone.utc),
        )
        test_db.add(closed_enrollment)
        test_db.commit()

        # Simulate scraper run: enrollment changes to open!
        open_enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        test_db.add(open_enrollment)
        test_db.commit()

        # Mock SessionLocal to use test_db
        with patch("notifications.send_notifs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = test_db

            # Step 3: Run notification job at minute :00
            job = NotificationJob(dry_run=False)
            result = job.execute()

            # Step 4: Verify results
            assert result["success"] is True
            assert result["notifications_sent"] == 3, "All 3 tiers should be notified at :00"

            # Verify all subscriptions are deactivated
            test_db.refresh(free_sub)
            test_db.refresh(plus_sub)
            test_db.refresh(pro_sub)

            assert free_sub.is_active is False, "Free subscription should be deactivated"
            assert free_sub.notification_count == 1
            assert free_sub.last_notified is not None

            assert plus_sub.is_active is False, "Plus subscription should be deactivated"
            assert plus_sub.notification_count == 1
            assert plus_sub.last_notified is not None

            assert pro_sub.is_active is False, "Pro subscription should be deactivated"
            assert pro_sub.notification_count == 1
            assert pro_sub.last_notified is not None

            # Verify notification logs created
            logs = test_db.query(NotificationLog).all()
            assert len(logs) == 3, "Should have 3 email notification logs"
            assert all(log.notification_type == "email" for log in logs)
            assert all(log.status == "sent" for log in logs)

    @pytest.mark.integration
    @freeze_time("2024-01-15 10:30:00")
    def test_free_and_plus_notified_on_minute_30(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_class: Class,
        free_user: Profile,
        plus_user: Profile,
        pro_user: Profile,
        mock_email_service_e2e,
        mock_sms_service_e2e,
    ):
        """
        Test that free and plus users are notified at :30, along with pro.

        Minute :30 is divisible by 30 (free), 5 (plus), and 1 (pro).
        """
        # Create subscriptions
        free_sub = Subscription(
            user_id=free_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        plus_sub = Subscription(
            user_id=plus_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        pro_sub = Subscription(
            user_id=pro_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add_all([free_sub, plus_sub, pro_sub])
        test_db.commit()

        # Create open enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        with patch("notifications.send_notifs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = test_db

            job = NotificationJob(dry_run=False)
            result = job.execute()

            assert result["success"] is True
            assert result["notifications_sent"] == 3, "Free, Plus, and Pro should all be notified at :30"

    @pytest.mark.integration
    @freeze_time("2024-01-15 10:05:00")
    def test_plus_and_pro_notified_on_minute_05(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_class: Class,
        free_user: Profile,
        plus_user: Profile,
        pro_user: Profile,
        mock_email_service_e2e,
        mock_sms_service_e2e,
    ):
        """
        Test that only plus and pro users are notified at :05 (not free).

        Minute :05 is divisible by 5 (plus) and 1 (pro), but not 30 (free).
        """
        # Create subscriptions
        free_sub = Subscription(
            user_id=free_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        plus_sub = Subscription(
            user_id=plus_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        pro_sub = Subscription(
            user_id=pro_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add_all([free_sub, plus_sub, pro_sub])
        test_db.commit()

        # Create open enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime(2024, 1, 15, 10, 5, tzinfo=timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        with patch("notifications.send_notifs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = test_db

            job = NotificationJob(dry_run=False)
            result = job.execute()

            assert result["success"] is True
            assert result["notifications_sent"] == 2, "Only Plus and Pro should be notified at :05"

            # Verify free user NOT deactivated, plus and pro ARE deactivated
            test_db.refresh(free_sub)
            test_db.refresh(plus_sub)
            test_db.refresh(pro_sub)

            assert free_sub.is_active is True, "Free subscription should still be active"
            assert plus_sub.is_active is False, "Plus subscription should be deactivated"
            assert pro_sub.is_active is False, "Pro subscription should be deactivated"

    @pytest.mark.integration
    @freeze_time("2024-01-15 10:07:00")
    def test_only_pro_notified_on_minute_07(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_class: Class,
        free_user: Profile,
        plus_user: Profile,
        pro_user: Profile,
        mock_email_service_e2e,
        mock_sms_service_e2e,
    ):
        """
        Test that only pro users are notified at :07 (not plus or free).

        Minute :07 is only divisible by 1 (pro), not 5 (plus) or 30 (free).
        """
        # Create subscriptions
        free_sub = Subscription(
            user_id=free_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        plus_sub = Subscription(
            user_id=plus_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        pro_sub = Subscription(
            user_id=pro_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add_all([free_sub, plus_sub, pro_sub])
        test_db.commit()

        # Create open enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime(2024, 1, 15, 10, 7, tzinfo=timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        with patch("notifications.send_notifs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = test_db

            job = NotificationJob(dry_run=False)
            result = job.execute()

            assert result["success"] is True
            assert result["notifications_sent"] == 1, "Only Pro should be notified at :07"

            # Verify only pro user deactivated
            test_db.refresh(free_sub)
            test_db.refresh(plus_sub)
            test_db.refresh(pro_sub)

            assert free_sub.is_active is True, "Free subscription should still be active"
            assert plus_sub.is_active is True, "Plus subscription should still be active"
            assert pro_sub.is_active is False, "Pro subscription should be deactivated"

    @pytest.mark.integration
    @freeze_time("2024-01-15 10:00:00")
    def test_no_notifications_for_closed_enrollment(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_class: Class,
        free_user: Profile,
        plus_user: Profile,
        pro_user: Profile,
        mock_email_service_e2e,
        mock_sms_service_e2e,
    ):
        """
        Test that no notifications are sent if enrollment is still closed.

        Even at :00 (when all tiers should be checked), closed enrollments
        should not trigger notifications.
        """
        # Create subscriptions
        free_sub = Subscription(
            user_id=free_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        plus_sub = Subscription(
            user_id=plus_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        pro_sub = Subscription(
            user_id=pro_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add_all([free_sub, plus_sub, pro_sub])
        test_db.commit()

        # Create CLOSED enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="closed",
            scraped_at=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        with patch("notifications.send_notifs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = test_db

            job = NotificationJob(dry_run=False)
            result = job.execute()

            assert result["success"] is True
            assert result["notifications_sent"] == 0, "No notifications should be sent for closed enrollment"

            # Verify all subscriptions still active
            test_db.refresh(free_sub)
            test_db.refresh(plus_sub)
            test_db.refresh(pro_sub)

            assert free_sub.is_active is True
            assert plus_sub.is_active is True
            assert pro_sub.is_active is True

    @pytest.mark.integration
    @freeze_time("2024-01-15 10:00:00")
    def test_pro_priority_delay(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_class: Class,
        free_user: Profile,
        pro_user: Profile,
        mock_email_service_e2e,
        mock_sms_service_e2e,
    ):
        """
        Test that Pro users get notified before other tiers (30 second delay).

        This verifies the PRO_PRIORITY_DELAY_SECONDS feature.
        """
        # Create subscriptions
        free_sub = Subscription(
            user_id=free_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        pro_sub = Subscription(
            user_id=pro_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add_all([free_sub, pro_sub])
        test_db.commit()

        # Create open enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        with patch("notifications.send_notifs.SessionLocal") as mock_session_local, \
             patch("notifications.send_notifs.time.sleep") as mock_sleep:
            mock_session_local.return_value.__enter__.return_value = test_db

            job = NotificationJob(dry_run=False)
            result = job.execute()

            # Verify time.sleep was called with PRO_PRIORITY_DELAY_SECONDS
            from notifications.constants import PRO_PRIORITY_DELAY_SECONDS
            mock_sleep.assert_called_once_with(PRO_PRIORITY_DELAY_SECONDS)

            assert result["success"] is True
            assert result["notifications_sent"] == 2

    @pytest.mark.integration
    @freeze_time("2024-01-15 10:00:00")
    def test_inactive_subscriptions_not_notified(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_class: Class,
        pro_user: Profile,
        mock_email_service_e2e,
        mock_sms_service_e2e,
    ):
        """
        Test that inactive subscriptions are not notified.

        Users who have already been notified (is_active=False) should not
        receive duplicate notifications.
        """
        # Create inactive subscription (already notified)
        inactive_sub = Subscription(
            user_id=pro_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=False,  # Already notified
            notification_count=1,
            last_notified=datetime(2024, 1, 15, 9, 55, tzinfo=timezone.utc),
        )
        test_db.add(inactive_sub)
        test_db.commit()

        # Create open enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        with patch("notifications.send_notifs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = test_db

            job = NotificationJob(dry_run=False)
            result = job.execute()

            assert result["success"] is True
            assert result["notifications_sent"] == 0, "Inactive subscriptions should not be notified"

            # Verify subscription still inactive with same notification count
            test_db.refresh(inactive_sub)
            assert inactive_sub.is_active is False
            assert inactive_sub.notification_count == 1  # Should not increment
