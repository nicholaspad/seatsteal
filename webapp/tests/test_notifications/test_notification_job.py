"""Tests for notification job (send_notifs.py)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from notifications.send_notifs import NotificationJob
from notifications.constants import (
    NOTIFICATION_CADENCE,
    USER_TIERS,
    PRO_PRIORITY_DELAY_SECONDS,
)
from models.subscription import Subscription
from models.user import Profile
from models.class_model import Class
from models.course import Course
from models.college import College
from models.enrollment import Enrollment
from models.stripe_subscription import StripeSubscription
from models.stripe_customer import StripeCustomer
from models.notification_log import NotificationLog
from models.scraper import Scraper
from tests.conftest import add_scraper_log
from utils.college_data_status import ORPHANED_BY_RESTART_MESSAGE


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    with patch("notifications.send_notifs.EmailService") as mock_class:
        mock_service = MagicMock()
        mock_service.send_course_notification = AsyncMock(return_value=True)
        mock_class.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_sms_service():
    """Mock SMS service."""
    with patch("notifications.send_notifs.SMSService") as mock_class:
        mock_service = MagicMock()
        mock_service.is_enabled = False
        mock_service.send_course_notification.return_value = True
        mock_class.return_value = mock_service
        yield mock_service


class TestNotificationJobInit:
    """Tests for NotificationJob initialization."""

    @pytest.mark.unit
    def test_init_normal_mode(self, mock_email_service, mock_sms_service):
        """Test initialization in normal mode."""
        job = NotificationJob(dry_run=False)

        assert job.dry_run is False
        assert job.email_service is not None
        assert job.sms_service is not None

    @pytest.mark.unit
    def test_init_dry_run_mode(self, mock_email_service, mock_sms_service):
        """Test initialization in dry-run mode."""
        job = NotificationJob(dry_run=True)

        assert job.dry_run is True


class TestFindNotificationsToSend:
    """Tests for _find_notifications_to_send method."""

    @pytest.fixture(autouse=True)
    def _fresh_successful_scrape(self, successful_scrape):
        """Existing tests assume the latest enrollment is from a successful run."""
        return successful_scrape

    @pytest.mark.unit
    def test_find_notifications_pro_minute(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test finding notifications for Pro users (every minute)."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_pro123",
            email=test_user.email,
        )
        test_db.add(customer)

        # Create Pro subscription
        pro_subscription = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_pro123",
            stripe_customer_id="cus_pro123",
            price_id="price_pro",
            tier="pro",
            status="active",
        )
        test_db.add(pro_subscription)

        # Create active subscription
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)

        # Create open enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        job = NotificationJob(dry_run=False)

        with patch("notifications.send_notifs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = test_db

            # Pro users should be included every minute
            with patch("notifications.send_notifs.datetime") as mock_datetime:
                mock_datetime.now.return_value.minute = 0  # Any minute

                notifications = job._find_notifications_to_send(test_db)

                # Should find the Pro user's notification
                assert len(notifications) > 0
                assert any(n["user_tier"] == "pro" for n in notifications)

    @pytest.mark.unit
    def test_find_notifications_plus_minute(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test finding notifications for Plus users (every 5 minutes)."""
        # Create Stripe customer first
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_plus123",
            email=test_user.email,
        )
        test_db.add(customer)

        # Create Plus subscription
        plus_subscription = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_plus123",
            stripe_customer_id="cus_plus123",
            price_id="price_plus",
            tier="plus",
            status="active",
        )
        test_db.add(plus_subscription)

        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)

        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        job = NotificationJob(dry_run=False)

        # Plus users should be included on minutes divisible by 5
        with patch("notifications.send_notifs.datetime") as mock_datetime:
            mock_datetime.now.return_value.minute = 5

            notifications = job._find_notifications_to_send(test_db)

            assert len(notifications) > 0
            assert any(n["user_tier"] == "plus" for n in notifications)

    @pytest.mark.unit
    def test_find_notifications_free_minute(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test finding notifications for Free users (every 30 minutes)."""
        # Free user (no stripe subscription)
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)

        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        job = NotificationJob(dry_run=False)

        # Free users should be included on minutes divisible by 30
        with patch("notifications.send_notifs.datetime") as mock_datetime:
            mock_datetime.now.return_value.minute = 30

            notifications = job._find_notifications_to_send(test_db)

            assert len(notifications) > 0
            assert any(n["user_tier"] == "free" for n in notifications)

    @pytest.mark.unit
    def test_find_notifications_closed_enrollment_excluded(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that subscriptions with closed enrollments are excluded."""
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)

        # Create CLOSED enrollment
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="closed",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        job = NotificationJob(dry_run=False)

        with patch("notifications.send_notifs.datetime") as mock_datetime:
            mock_datetime.now.return_value.minute = 0

            notifications = job._find_notifications_to_send(test_db)

            # Should not find notifications for closed enrollments
            assert len(notifications) == 0

    @pytest.mark.unit
    def test_find_notifications_inactive_subscription_excluded(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that inactive subscriptions are excluded."""
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=False,  # Inactive
        )
        test_db.add(subscription)

        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()

        job = NotificationJob(dry_run=False)

        with patch("notifications.send_notifs.datetime") as mock_datetime:
            mock_datetime.now.return_value.minute = 0

            notifications = job._find_notifications_to_send(test_db)

            assert len(notifications) == 0


class TestSeatAlertQueryRegression:
    """Open-seat selection must use the latest successful scrape, not stale opens."""

    def _subscribe_user(
        self,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college: College,
    ) -> Subscription:
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)
        test_db.commit()
        return subscription

    def _find_at_minute_zero(self, test_db: Session):
        job = NotificationJob(dry_run=False)
        with patch("notifications.send_notifs.datetime") as mock_datetime:
            mock_datetime.now.return_value.minute = 0
            return job._find_notifications_to_send(test_db)

    def _add_enrollment(
        self,
        test_db: Session,
        test_class: Class,
        test_college: College,
        *,
        status: str,
        scraped_at: datetime,
    ) -> Enrollment:
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status=status,
            scraped_at=scraped_at,
        )
        test_db.add(enrollment)
        test_db.commit()
        return enrollment

    def _add_scraper(
        self,
        test_db: Session,
        test_college: College,
        last_success_at: datetime,
    ) -> Scraper:
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
            last_success_at=last_success_at,
            last_run_at=last_success_at,
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)
        return scraper

    @pytest.mark.unit
    def test_latest_record_not_open_after_earlier_open_sends_no_alert(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """A later closed/full scrape must win over an older open row."""
        now = datetime.now(timezone.utc)
        scraper = self._add_scraper(test_db, test_college, now)
        add_scraper_log(
            test_db,
            scraper,
            outcome="success",
            started_at=now - timedelta(hours=1),
            completed_at=now,
        )
        self._subscribe_user(test_db, test_user, test_class, test_college)
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="open",
            scraped_at=now - timedelta(minutes=20),
        )
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="closed",
            scraped_at=now - timedelta(minutes=5),
        )

        assert self._find_at_minute_zero(test_db) == []

    @pytest.mark.unit
    def test_latest_record_open_and_from_successful_run_sends_alert(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        now = datetime.now(timezone.utc)
        scraper = self._add_scraper(test_db, test_college, now)
        add_scraper_log(
            test_db,
            scraper,
            outcome="success",
            started_at=now - timedelta(hours=1),
            completed_at=now,
        )
        self._subscribe_user(test_db, test_user, test_class, test_college)
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="closed",
            scraped_at=now - timedelta(minutes=20),
        )
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="open",
            scraped_at=now - timedelta(minutes=5),
        )

        notifications = self._find_at_minute_zero(test_db)
        assert len(notifications) == 1
        assert notifications[0]["class_id"] == test_class.class_id

    @pytest.mark.unit
    def test_stale_school_is_suppressed(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """#249 two consecutive failed-empty runs: banner-stale, no seat alert."""
        now = datetime.now(timezone.utc)
        success_at = now - timedelta(hours=2)
        scraper = self._add_scraper(test_db, test_college, success_at)
        add_scraper_log(
            test_db,
            scraper,
            outcome="success",
            started_at=success_at - timedelta(minutes=30),
            completed_at=success_at,
        )
        add_scraper_log(
            test_db,
            scraper,
            outcome="error",
            started_at=now - timedelta(hours=1),
            completed_at=now - timedelta(hours=1) + timedelta(minutes=5),
            courses_created=0,
        )
        add_scraper_log(
            test_db,
            scraper,
            outcome="error",
            started_at=now - timedelta(minutes=20),
            completed_at=now - timedelta(minutes=15),
            courses_created=0,
        )
        self._subscribe_user(test_db, test_user, test_class, test_college)
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="open",
            scraped_at=success_at - timedelta(minutes=5),
        )

        assert self._find_at_minute_zero(test_db) == []

    @pytest.mark.unit
    def test_record_from_failed_or_orphaned_run_is_ignored(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        now = datetime.now(timezone.utc)
        success_at = now - timedelta(hours=2)
        scraper = self._add_scraper(test_db, test_college, success_at)
        add_scraper_log(
            test_db,
            scraper,
            outcome="success",
            started_at=success_at - timedelta(minutes=30),
            completed_at=success_at,
        )
        add_scraper_log(
            test_db,
            scraper,
            outcome="error",
            started_at=now - timedelta(minutes=20),
            completed_at=now - timedelta(minutes=10),
            courses_created=0,
            error_message=ORPHANED_BY_RESTART_MESSAGE,
        )
        self._subscribe_user(test_db, test_user, test_class, test_college)
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="closed",
            scraped_at=success_at - timedelta(minutes=5),
        )
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="open",
            scraped_at=now - timedelta(minutes=15),
        )

        assert self._find_at_minute_zero(test_db) == []

    @pytest.mark.unit
    def test_record_from_before_latest_successful_run_is_ignored(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        now = datetime.now(timezone.utc)
        old_success = now - timedelta(hours=3)
        new_success = now - timedelta(minutes=10)
        scraper = self._add_scraper(test_db, test_college, new_success)
        add_scraper_log(
            test_db,
            scraper,
            outcome="success",
            started_at=old_success - timedelta(minutes=30),
            completed_at=old_success,
        )
        add_scraper_log(
            test_db,
            scraper,
            outcome="success",
            started_at=new_success - timedelta(minutes=20),
            completed_at=new_success,
        )
        self._subscribe_user(test_db, test_user, test_class, test_college)
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="open",
            scraped_at=old_success - timedelta(minutes=5),
        )

        assert self._find_at_minute_zero(test_db) == []

    @pytest.mark.unit
    def test_two_active_plans_return_one_subscription_row(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_course: Course,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        now = datetime.now(timezone.utc)
        scraper = self._add_scraper(test_db, test_college, now)
        add_scraper_log(
            test_db,
            scraper,
            outcome="success",
            started_at=now - timedelta(hours=1),
            completed_at=now,
        )
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_two_plans",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.add(
            StripeSubscription(
                user_id=test_user.id,
                stripe_subscription_id="sub_plus_dup",
                stripe_customer_id="cus_two_plans",
                price_id="price_plus",
                tier="plus",
                status="active",
            )
        )
        test_db.add(
            StripeSubscription(
                user_id=test_user.id,
                stripe_subscription_id="sub_pro_dup",
                stripe_customer_id="cus_two_plans",
                price_id="price_pro",
                tier="pro",
                status="active",
            )
        )
        self._subscribe_user(test_db, test_user, test_class, test_college)
        self._add_enrollment(
            test_db,
            test_class,
            test_college,
            status="open",
            scraped_at=now - timedelta(minutes=5),
        )
        test_db.commit()

        notifications = self._find_at_minute_zero(test_db)
        assert len(notifications) == 1
        assert notifications[0]["user_tier"] in {"plus", "pro"}


class TestSendNotification:
    """Tests for _send_notification method."""

    @pytest.mark.unit
    def test_send_notification_email_success(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test successful email notification sending."""
        # Create subscription in database
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        notification = {
            "subscription_id": subscription.id,
            "user_id": test_user.id,
            "course_code": "CS 101",
            "course_title": "Intro to CS",
            "section_code": "A1",
            "class_number": "12345",
            "college_name": "Test University",
            "college_id": test_college.id,
            "user_email": test_user.email,
            "user_phone": None,
            "user_tier": "free",
        }

        job = NotificationJob(dry_run=False)
        job._send_notification(notification, test_db)

        # Verify email was sent
        mock_email_service.send_course_notification.assert_called_once()

        # Verify notification log was created
        logs = test_db.query(NotificationLog).all()
        assert len(logs) == 1
        assert logs[0].notification_type == "email"
        assert logs[0].status == "sent"

    @pytest.mark.unit
    def test_send_notification_with_sms(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test notification sending with SMS enabled."""
        mock_sms_service.is_enabled = True

        # Create subscription in database
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        notification = {
            "subscription_id": subscription.id,
            "user_id": test_user.id,
            "course_code": "CS 101",
            "course_title": "Intro to CS",
            "section_code": "A1",
            "class_number": "12345",
            "college_name": "Test University",
            "college_id": test_college.id,
            "user_email": test_user.email,
            "user_phone": "+1234567890",
            "user_tier": "pro",
            "sms_enabled": True,
        }

        job = NotificationJob(dry_run=False)
        job._send_notification(notification, test_db)

        # Verify both email and SMS were sent
        mock_email_service.send_course_notification.assert_called_once()
        mock_sms_service.send_course_notification.assert_called_once()

        # Verify two notification logs created
        logs = test_db.query(NotificationLog).all()
        assert len(logs) == 2
        assert any(log.notification_type == "email" for log in logs)
        assert any(log.notification_type == "sms" for log in logs)

    @pytest.mark.unit
    def test_send_notification_skips_sms_when_college_sms_disabled(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Twilio ready is not enough; the school must also have SMS on."""
        mock_sms_service.is_enabled = True
        test_college.sms_enabled = False

        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        notification = {
            "subscription_id": subscription.id,
            "user_id": test_user.id,
            "course_code": "CS 101",
            "course_title": "Intro to CS",
            "section_code": "A1",
            "class_number": "12345",
            "college_name": "Test University",
            "college_id": test_college.id,
            "user_email": test_user.email,
            "user_phone": "+1234567890",
            "user_tier": "pro",
            "sms_enabled": False,
        }

        job = NotificationJob(dry_run=False)
        job._send_notification(notification, test_db)

        mock_email_service.send_course_notification.assert_called_once()
        mock_sms_service.send_course_notification.assert_not_called()
        logs = test_db.query(NotificationLog).all()
        assert len(logs) == 1
        assert logs[0].notification_type == "email"

    @pytest.mark.unit
    def test_send_notification_dry_run_mode(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that dry-run mode doesn't send actual notifications."""
        notification = {
            "subscription_id": 1,
            "user_id": test_user.id,
            "course_code": "CS 101",
            "course_title": "Intro to CS",
            "section_code": "A1",
            "class_number": "12345",
            "college_name": "Test University",
            "college_id": test_college.id,
            "user_email": test_user.email,
            "user_phone": None,
            "user_tier": "free",
        }

        job = NotificationJob(dry_run=True)
        job._send_notification(notification, test_db)

        # Verify no emails were sent
        mock_email_service.send_course_notification.assert_not_called()

        # Verify no logs were created
        logs = test_db.query(NotificationLog).all()
        assert len(logs) == 0

    @pytest.mark.unit
    def test_send_notification_email_failure_raises(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that email failure raises exception."""
        mock_email_service.send_course_notification = AsyncMock(return_value=False)

        notification = {
            "subscription_id": 1,
            "user_id": test_user.id,
            "course_code": "CS 101",
            "course_title": "Intro to CS",
            "section_code": "A1",
            "class_number": "12345",
            "college_name": "Test University",
            "college_id": test_college.id,
            "user_email": test_user.email,
            "user_phone": None,
            "user_tier": "free",
        }

        job = NotificationJob(dry_run=False)

        with pytest.raises(Exception, match="Failed to send email"):
            job._send_notification(notification, test_db)


class TestDeactivateSubscriptions:
    """Tests for _deactivate_subscriptions method."""

    @pytest.mark.unit
    def test_deactivate_subscriptions(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test deactivating subscriptions after notification."""
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
            notification_count=0,
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        job = NotificationJob(dry_run=False)
        job._deactivate_subscriptions(test_db, [subscription.id])

        test_db.refresh(subscription)

        assert subscription.is_active is False
        assert subscription.notification_count == 1
        assert subscription.last_notified is not None

    @pytest.mark.unit
    def test_deactivate_multiple_subscriptions(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_class: Class,
        mock_email_service,
        mock_sms_service,
    ):
        """Test deactivating multiple subscriptions."""
        sub1 = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        sub2 = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add_all([sub1, sub2])
        test_db.commit()

        job = NotificationJob(dry_run=False)
        job._deactivate_subscriptions(test_db, [sub1.id, sub2.id])

        test_db.refresh(sub1)
        test_db.refresh(sub2)

        assert sub1.is_active is False
        assert sub2.is_active is False


class TestExecute:
    """Tests for execute method (main job runner)."""

    @pytest.mark.unit
    def test_execute_no_notifications(self, mock_email_service, mock_sms_service):
        """Test execute when no notifications need to be sent."""
        job = NotificationJob(dry_run=False)

        with patch.object(job, "_find_notifications_to_send", return_value=[]):
            result = job.execute()

            assert result["success"] is True
            assert result["notifications_sent"] == 0

    @pytest.mark.unit
    def test_execute_dry_run_mode(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        mock_email_service,
        mock_sms_service,
    ):
        """Test execute in dry-run mode."""
        notification = {
            "subscription_id": 1,
            "user_id": test_user.id,
            "course_code": "CS 101",
            "course_title": "Test",
            "section_code": "A1",
            "class_number": "12345",
            "college_name": "Test U",
            "college_id": test_college.id,
            "user_email": "test@test.com",
            "user_phone": None,
            "user_tier": "free",
        }

        job = NotificationJob(dry_run=True)

        with patch.object(
            job, "_find_notifications_to_send", return_value=[notification]
        ), patch("notifications.send_notifs.SessionLocal") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db

            result = job.execute()

            assert result["success"] is True
            assert result["dry_run"] is True
            # In dry run, notifications are "sent" but not actually sent
            mock_email_service.send_course_notification.assert_not_called()

    @pytest.mark.unit
    def test_execute_with_pro_priority_delay(
        self,
        test_db: Session,
        test_college: College,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that Pro users get priority (delay before Plus/Free)."""
        # This is difficult to test without actual time.sleep, but we can verify
        # the structure
        job = NotificationJob(dry_run=False)

        pro_notif = {
            "subscription_id": 1,
            "user_id": "uuid1",
            "user_tier": "pro",
            "course_code": "CS 101",
            "course_title": "Test",
            "section_code": "A1",
            "class_number": "12345",
            "college_name": "Test U",
            "college_id": 1,
            "user_email": "pro@test.com",
            "user_phone": None,
        }
        free_notif = {
            "subscription_id": 2,
            "user_id": "uuid2",
            "user_tier": "free",
            "course_code": "CS 102",
            "course_title": "Test 2",
            "section_code": "B1",
            "class_number": "12346",
            "college_name": "Test U",
            "college_id": 1,
            "user_email": "free@test.com",
            "user_phone": None,
        }

        with patch.object(
            job, "_find_notifications_to_send", return_value=[pro_notif, free_notif]
        ), patch("notifications.send_notifs.SessionLocal") as mock_session, patch(
            "notifications.send_notifs.time.sleep"
        ) as mock_sleep:
            mock_session.return_value.__enter__.return_value = test_db

            result = job.execute()

            # Should have waited before sending free notifications
            mock_sleep.assert_called_once_with(PRO_PRIORITY_DELAY_SECONDS)

    @pytest.mark.unit
    def test_execute_handles_error_gracefully(
        self, mock_email_service, mock_sms_service
    ):
        """Test that execute handles errors gracefully."""
        job = NotificationJob(dry_run=False)

        with patch.object(
            job, "_find_notifications_to_send", side_effect=Exception("Database error")
        ):
            result = job.execute()

            assert result["success"] is False
            assert "Database error" in result["error"]
            assert "duration_ms" in result
