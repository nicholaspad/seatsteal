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
        """Test message building with short college name."""
        # Set Twilio env vars temporarily to empty (service will be disabled)
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        message = service._build_notification_message("CS101", "A", "Test University")

        assert len(message) <= 160
        assert "SeatSteal:" in message
        assert "CS101 A" in message
        assert "Test University" in message
        assert "is OPEN!" in message

    def test_build_notification_message_truncates_long_college(self):
        """Test message truncates long college names to fit in one segment."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()
        long_college = "The University of California San Diego School of Engineering and Applied Sciences Extended Name"
        message = service._build_notification_message("CS101", "A", long_college)

        assert len(message) <= 160
        assert "SeatSteal:" in message
        assert "CS101 A" in message
        assert "is OPEN!" in message
        # Long name should be truncated with ellipsis
        assert "..." in message or len(long_college) <= 100

    def test_build_notification_message_max_length(self):
        """Test message never exceeds 160 characters."""
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

        from notifications.sms_service import SMSService

        service = SMSService()

        # Test with various inputs
        test_cases = [
            ("CS101", "A", "MIT"),
            ("CSCI-UA.0101-001", "LAB-A1", "New York University"),
            ("INTRODUCTION TO COMPUTER SCIENCE", "SECTION-001", "Harvard University"),
        ]

        for course, section, college in test_cases:
            message = service._build_notification_message(course, section, college)
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
            course_code="CS101",
            section_code="A",
            college_name="Test University",
        )
        assert result is False


class TestSMSServiceSending:
    """Test SMS sending with mocked Twilio client."""

    def test_send_success(self):
        """Test successful SMS sending."""
        os.environ["TWILIO_ACCOUNT_SID"] = "test_sid"
        os.environ["TWILIO_AUTH_TOKEN"] = "test_token"
        os.environ["TWILIO_FROM_NUMBER"] = "+15559999999"

        with patch.dict("sys.modules", {"twilio.rest": MagicMock()}):
            # Mock the Twilio Client
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.sid = "SM123456"
            mock_client.messages.create.return_value = mock_message

            with patch("twilio.rest.Client", return_value=mock_client):
                import importlib
                import notifications.sms_service

                importlib.reload(notifications.sms_service)
                from notifications.sms_service import SMSService

                service = SMSService()
                # Manually set the client and from_number for testing
                service.client = mock_client
                service.from_number = "+15559999999"

                result = service.send_course_notification(
                    to_phone="+15551234567",
                    course_code="CS101",
                    section_code="A",
                    college_name="Test University",
                )

                assert result is True
                mock_client.messages.create.assert_called_once()
                call_kwargs = mock_client.messages.create.call_args[1]
                assert "+15551234567" == call_kwargs["to"]
                assert "+15559999999" == call_kwargs["from_"]
                assert "CS101" in call_kwargs["body"]
                assert "SeatSteal" in call_kwargs["body"]

        # Clean up
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""

    def test_send_failure(self):
        """Test SMS sending failure."""
        os.environ["TWILIO_ACCOUNT_SID"] = "test_sid"
        os.environ["TWILIO_AUTH_TOKEN"] = "test_token"
        os.environ["TWILIO_FROM_NUMBER"] = "+15559999999"

        with patch.dict("sys.modules", {"twilio.rest": MagicMock()}):
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("Twilio error")

            with patch("twilio.rest.Client", return_value=mock_client):
                import importlib
                import notifications.sms_service

                importlib.reload(notifications.sms_service)
                from notifications.sms_service import SMSService

                service = SMSService()
                # Manually set the client for testing
                service.client = mock_client

                result = service.send_course_notification(
                    to_phone="+15551234567",
                    course_code="CS101",
                    section_code="A",
                    college_name="Test University",
                )

                assert result is False

        # Clean up
        os.environ["TWILIO_ACCOUNT_SID"] = ""
        os.environ["TWILIO_AUTH_TOKEN"] = ""
        os.environ["TWILIO_FROM_NUMBER"] = ""
