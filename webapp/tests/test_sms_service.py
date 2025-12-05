"""Tests for SMS service."""

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path

# Set environment variables for testing BEFORE any imports
os.environ["VITE_SUPABASE_URL"] = "https://test.supabase.co"
os.environ["VITE_SUPABASE_ANON_KEY"] = "test_anon_key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test_key"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/seatsteal_test"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["PYTHON_ENV"] = "test"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test_access_key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test_secret_key"
os.environ["AWS_SES_FROM_EMAIL"] = "test@example.com"

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent
sys.path.insert(0, str(webapp_dir))


class TestSMSServiceMessageBuilding:
    """Test SMS message building functionality."""

    def test_build_notification_message_short(self):
        """Test message building with short course name."""
        # Set Twilio env vars temporarily to empty (service will be disabled)
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        message = service._build_notification_message(
            "Intro to CS", "A", "Test University"
        )

        assert len(message) <= 160
        assert "SeatSteal:" in message
        assert "Intro to CS" in message
        assert "A" in message
        assert "is OPEN!" in message

    def test_build_notification_message_truncates_long_course_name(self):
        """Test message truncates long course names to fit in one segment."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        # This course name is long enough to require truncation
        long_course_name = "Introduction to Computer Science and Programming with Applications in Data Science and Machine Learning and Advanced Statistical Methods"
        message = service._build_notification_message(
            long_course_name, "A", "Test University"
        )

        assert len(message) <= 160
        assert "SeatSteal:" in message
        assert "is OPEN!" in message
        # Long name should be truncated with ellipsis
        assert "..." in message

    def test_build_notification_message_max_length(self):
        """Test message never exceeds 160 characters."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Test with various inputs (course_name, section, college)
        test_cases = [
            ("Introduction to Computer Science", "A", "MIT"),
            ("Data Structures and Algorithms", "LAB-A1", "New York University"),
            (
                "Advanced Topics in Machine Learning and Artificial Intelligence",
                "SECTION-001",
                "Harvard University",
            ),
        ]

        for course_name, section, college in test_cases:
            message = service._build_notification_message(course_name, section, college)
            assert (
                len(message) <= 160
            ), f"Message too long ({len(message)} chars): {message}"


class TestSMSServicePhoneNormalization:
    """Test phone number normalization."""

    def test_normalize_us_10_digit(self):
        """Test normalizing 10-digit US numbers."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        assert service._normalize_phone("5551234567") == "+15551234567"

    def test_normalize_us_11_digit(self):
        """Test normalizing 11-digit US numbers with leading 1."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        assert service._normalize_phone("15551234567") == "+15551234567"

    def test_normalize_e164_format(self):
        """Test normalizing numbers already in E.164 format."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        assert service._normalize_phone("+15551234567") == "+15551234567"

    def test_normalize_formatted_number(self):
        """Test normalizing formatted phone numbers."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        assert service._normalize_phone("(555) 123-4567") == "+15551234567"
        assert service._normalize_phone("555-123-4567") == "+15551234567"
        assert service._normalize_phone("555.123.4567") == "+15551234567"

    def test_normalize_invalid_short(self):
        """Test normalizing too-short numbers returns None."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        assert service._normalize_phone("555123") is None
        assert service._normalize_phone("") is None
        assert service._normalize_phone(None) is None


class TestSMSServiceEnabled:
    """Test SMS service enabled/disabled logic."""

    def test_service_disabled_when_not_configured(self):
        """Test service is disabled when Twilio not configured."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        assert service.is_enabled is False

    def test_send_returns_false_when_disabled(self):
        """Test send_course_notification returns False when disabled."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        result = service.send_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )
        assert result is False


class TestSMSServiceSending:
    """Test SMS sending with mocked Twilio client."""

    def test_send_success(self):
        """Test successful SMS sending by directly injecting a mock client."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        # Create service (will be disabled since env vars are empty)
        service = SMSService()

        # Manually inject mock client to simulate enabled state
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_client.messages.create.return_value = mock_message

        service.client = mock_client
        service.from_number = "+15559999999"

        result = service.send_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )

        assert result is True
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "+15551234567" == call_kwargs["to"]
        assert "+15559999999" == call_kwargs["from_"]
        assert "Introduction to Computer Science" in call_kwargs["body"]
        assert "SeatSteal" in call_kwargs["body"]

    def test_send_failure(self):
        """Test SMS sending failure."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        # Create service (will be disabled since env vars are empty)
        service = SMSService()

        # Manually inject mock client that raises an exception
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Twilio error")

        service.client = mock_client
        service.from_number = "+15559999999"

        result = service.send_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )

        assert result is False


class TestSMSServiceRateLimiting:
    """Test SMS rate limiting functionality."""

    def test_rate_limit_interval_is_one_second(self):
        """Test that rate limit interval is set to 1 second."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        assert service.RATE_LIMIT_INTERVAL == 1.0

    def test_rate_limiting_enforces_delay(self):
        """Test that rate limiting enforces delay between sends."""
        import time

        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Manually inject mock client
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_client.messages.create.return_value = mock_message
        service.client = mock_client
        service.from_number = "+15559999999"

        # Send first message
        start_time = time.time()
        service.send_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )
        first_send_time = time.time()

        # Send second message - should be rate limited
        service.send_course_notification(
            to_phone="+15551234568",
            course_name="Data Structures",
            section_code="B",
            college_name="Test University",
        )
        second_send_time = time.time()

        # The second send should have waited at least 1 second
        # Allow small tolerance for timing variations
        elapsed_between_sends = second_send_time - first_send_time
        assert (
            elapsed_between_sends >= 0.9
        ), f"Rate limiting should enforce ~1s delay, got {elapsed_between_sends}s"

    def test_no_rate_limit_delay_on_first_send(self):
        """Test that first send doesn't have rate limit delay."""
        import time

        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Manually inject mock client
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_client.messages.create.return_value = mock_message
        service.client = mock_client
        service.from_number = "+15559999999"

        # First send should be immediate (no rate limit wait)
        start_time = time.time()
        service.send_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )
        elapsed = time.time() - start_time

        # First send should be fast (under 0.5s, no rate limit)
        assert elapsed < 0.5, f"First send should be immediate, took {elapsed}s"


class TestSMSServiceQueue:
    """Test SMS queue functionality."""

    def test_queue_course_notification(self):
        """Test queuing a course notification."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Queue should start empty
        assert service.queue_size == 0

        # Queue a message
        result = service.queue_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )

        assert result is True
        assert service.queue_size == 1

        # Queue another message
        service.queue_course_notification(
            to_phone="+15551234568",
            course_name="Data Structures",
            section_code="B",
            college_name="Test University",
        )

        assert service.queue_size == 2

    def test_queue_rejects_invalid_phone(self):
        """Test that queuing rejects invalid phone numbers."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Empty phone
        result = service.queue_course_notification(
            to_phone="",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )
        assert result is False
        assert service.queue_size == 0

        # Invalid phone
        result = service.queue_course_notification(
            to_phone="123",  # Too short
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )
        assert result is False
        assert service.queue_size == 0

    def test_flush_queue_when_disabled(self):
        """Test flushing queue when service is disabled."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Queue some messages
        service.queue_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )
        service.queue_course_notification(
            to_phone="+15551234568",
            course_name="Data Structures",
            section_code="B",
            college_name="Test University",
        )

        assert service.queue_size == 2

        # Flush should fail all messages since service is disabled
        result = service.flush_queue()

        assert result["sent"] == 0
        assert result["failed"] == 2
        assert result["total"] == 2
        assert service.queue_size == 0

    def test_flush_queue_with_enabled_service(self):
        """Test flushing queue with enabled service."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Manually inject mock client
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_client.messages.create.return_value = mock_message
        service.client = mock_client
        service.from_number = "+15559999999"

        # Queue messages
        service.queue_course_notification(
            to_phone="+15551234567",
            course_name="Introduction to Computer Science",
            section_code="A",
            college_name="Test University",
        )
        service.queue_course_notification(
            to_phone="+15551234568",
            course_name="Data Structures",
            section_code="B",
            college_name="Test University",
        )

        # Flush should send all messages
        result = service.flush_queue()

        assert result["sent"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2
        assert service.queue_size == 0
        assert mock_client.messages.create.call_count == 2

    def test_flush_empty_queue(self):
        """Test flushing empty queue."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        result = service.flush_queue()

        assert result["sent"] == 0
        assert result["failed"] == 0
        assert result["total"] == 0
