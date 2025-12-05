"""Tests for notification job functionality."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from models.notification_log import NotificationLog
from models.subscription import Subscription
from models.class_model import Class
from models.course import Course
from models.college import College
from models.user import Profile


class TestNotificationJobLogging:
    """Tests for notification job's logging functionality."""

    @pytest.fixture
    def mock_email_service(self):
        """Create a mock email service."""
        with patch("notifications.send_notifs.EmailService") as mock:
            instance = mock.return_value
            instance.send_course_notification = AsyncMock(return_value=True)
            yield instance

    @pytest.fixture
    def mock_sms_service(self):
        """Create a mock SMS service."""
        with patch("notifications.send_notifs.SMSService") as mock:
            instance = mock.return_value
            instance.is_enabled = True
            instance.send_course_notification = MagicMock(return_value=True)
            yield instance

    @pytest.fixture
    def notification_data(
        self,
        test_subscription: Subscription,
        test_class: Class,
        test_course: Course,
        test_college: College,
        test_user: Profile,
    ):
        """Create notification data for testing."""
        return {
            "subscription_id": test_subscription.id,
            "user_id": str(test_user.id),
            "class_id": test_class.class_id,
            "course_code": test_course.course_code,
            "course_title": test_course.title,
            "class_number": test_class.class_number,
            "section_code": test_class.section_code,
            "college_id": test_college.id,
            "college_name": test_college.name,
            "user_email": test_user.email,
            "user_phone": test_user.phone,
            "user_tier": "free",
        }

    @pytest.mark.unit
    def test_send_notification_logs_email(
        self,
        test_db: Session,
        notification_data: dict,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that sending a notification logs the email."""
        from notifications.send_notifs import NotificationJob

        with patch(
            "notifications.send_notifs.EmailService", return_value=mock_email_service
        ), patch("notifications.send_notifs.SMSService", return_value=mock_sms_service):
            job = NotificationJob(dry_run=False)
            job.email_service = mock_email_service
            job.sms_service = mock_sms_service

            # Send the notification
            job._send_notification(notification_data, test_db)
            test_db.commit()

            # Verify email log was created
            email_logs = (
                test_db.query(NotificationLog)
                .filter(NotificationLog.notification_type == "email")
                .all()
            )
            assert len(email_logs) == 1
            email_log = email_logs[0]
            assert email_log.subscription_id == notification_data["subscription_id"]
            assert email_log.college_id == notification_data["college_id"]
            assert email_log.status == "sent"
            assert notification_data["course_title"] in email_log.message

    @pytest.mark.unit
    def test_send_notification_logs_sms(
        self,
        test_db: Session,
        notification_data: dict,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that sending a notification logs the SMS when phone is provided."""
        from notifications.send_notifs import NotificationJob

        with patch(
            "notifications.send_notifs.EmailService", return_value=mock_email_service
        ), patch("notifications.send_notifs.SMSService", return_value=mock_sms_service):
            job = NotificationJob(dry_run=False)
            job.email_service = mock_email_service
            job.sms_service = mock_sms_service

            # Send the notification (with phone number)
            job._send_notification(notification_data, test_db)
            test_db.commit()

            # Verify SMS log was created
            sms_logs = (
                test_db.query(NotificationLog)
                .filter(NotificationLog.notification_type == "sms")
                .all()
            )
            assert len(sms_logs) == 1
            sms_log = sms_logs[0]
            assert sms_log.subscription_id == notification_data["subscription_id"]
            assert sms_log.college_id == notification_data["college_id"]
            assert sms_log.status == "sent"
            assert notification_data["course_title"] in sms_log.message

    @pytest.mark.unit
    def test_send_notification_logs_both_email_and_sms(
        self,
        test_db: Session,
        notification_data: dict,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that sending a notification creates logs for both email and SMS."""
        from notifications.send_notifs import NotificationJob

        with patch(
            "notifications.send_notifs.EmailService", return_value=mock_email_service
        ), patch("notifications.send_notifs.SMSService", return_value=mock_sms_service):
            job = NotificationJob(dry_run=False)
            job.email_service = mock_email_service
            job.sms_service = mock_sms_service

            # Send the notification
            job._send_notification(notification_data, test_db)
            test_db.commit()

            # Verify both logs were created
            all_logs = test_db.query(NotificationLog).all()
            assert len(all_logs) == 2

            types = {log.notification_type for log in all_logs}
            assert types == {"email", "sms"}

    @pytest.mark.unit
    def test_send_notification_no_sms_without_phone(
        self,
        test_db: Session,
        notification_data: dict,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that SMS log is not created when user has no phone."""
        from notifications.send_notifs import NotificationJob

        # Remove phone from notification data
        notification_data["user_phone"] = None

        with patch(
            "notifications.send_notifs.EmailService", return_value=mock_email_service
        ), patch("notifications.send_notifs.SMSService", return_value=mock_sms_service):
            job = NotificationJob(dry_run=False)
            job.email_service = mock_email_service
            job.sms_service = mock_sms_service

            # Send the notification
            job._send_notification(notification_data, test_db)
            test_db.commit()

            # Verify only email log was created (no SMS)
            all_logs = test_db.query(NotificationLog).all()
            assert len(all_logs) == 1
            assert all_logs[0].notification_type == "email"

    @pytest.mark.unit
    def test_send_notification_logs_failed_email(
        self,
        test_db: Session,
        notification_data: dict,
        mock_sms_service,
    ):
        """Test that failed email is logged with 'failed' status."""
        from notifications.send_notifs import NotificationJob

        # Create a mock email service that returns False (failure)
        mock_failed_email = MagicMock()
        mock_failed_email.send_course_notification = AsyncMock(return_value=False)

        with patch(
            "notifications.send_notifs.EmailService", return_value=mock_failed_email
        ), patch("notifications.send_notifs.SMSService", return_value=mock_sms_service):
            job = NotificationJob(dry_run=False)
            job.email_service = mock_failed_email
            job.sms_service = mock_sms_service

            # Send the notification (should raise exception for failed email)
            with pytest.raises(Exception, match="Failed to send email"):
                job._send_notification(notification_data, test_db)

            test_db.commit()

            # Verify email log shows 'failed' status
            email_log = (
                test_db.query(NotificationLog)
                .filter(NotificationLog.notification_type == "email")
                .first()
            )
            assert email_log is not None
            assert email_log.status == "failed"

    @pytest.mark.unit
    def test_send_notification_logs_failed_sms(
        self,
        test_db: Session,
        notification_data: dict,
        mock_email_service,
    ):
        """Test that failed SMS is logged with 'failed' status."""
        from notifications.send_notifs import NotificationJob

        # Create a mock SMS service that returns False (failure)
        mock_failed_sms = MagicMock()
        mock_failed_sms.is_enabled = True
        mock_failed_sms.send_course_notification = MagicMock(return_value=False)

        with patch(
            "notifications.send_notifs.EmailService", return_value=mock_email_service
        ), patch("notifications.send_notifs.SMSService", return_value=mock_failed_sms):
            job = NotificationJob(dry_run=False)
            job.email_service = mock_email_service
            job.sms_service = mock_failed_sms

            # Send the notification (email succeeds, SMS fails)
            job._send_notification(notification_data, test_db)
            test_db.commit()

            # Verify SMS log shows 'failed' status
            sms_log = (
                test_db.query(NotificationLog)
                .filter(NotificationLog.notification_type == "sms")
                .first()
            )
            assert sms_log is not None
            assert sms_log.status == "failed"

            # Email should still be 'sent'
            email_log = (
                test_db.query(NotificationLog)
                .filter(NotificationLog.notification_type == "email")
                .first()
            )
            assert email_log is not None
            assert email_log.status == "sent"

    @pytest.mark.unit
    def test_dry_run_does_not_log(
        self,
        test_db: Session,
        notification_data: dict,
        mock_email_service,
        mock_sms_service,
    ):
        """Test that dry run mode does not create notification logs."""
        from notifications.send_notifs import NotificationJob

        with patch(
            "notifications.send_notifs.EmailService", return_value=mock_email_service
        ), patch("notifications.send_notifs.SMSService", return_value=mock_sms_service):
            job = NotificationJob(dry_run=True)
            job.email_service = mock_email_service
            job.sms_service = mock_sms_service

            # Send the notification in dry run mode
            job._send_notification(notification_data, test_db)
            test_db.commit()

            # Verify no logs were created
            all_logs = test_db.query(NotificationLog).all()
            assert len(all_logs) == 0
