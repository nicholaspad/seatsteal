"""Tests for the shared seat-alert / waitlist SMS gate."""

from notifications.channel import choose_notification_channel, should_send_sms


class TestShouldSendSms:
    def test_requires_phone_and_opt_in(self):
        assert should_send_sms("5551234567", True) is True

    def test_phone_without_opt_in_is_email(self):
        assert should_send_sms("5551234567", False) is False

    def test_opt_in_without_phone_is_email(self):
        assert should_send_sms(None, True) is False
        assert should_send_sms("", True) is False
        assert should_send_sms("   ", True) is False

    def test_requires_twilio_and_college_sms(self):
        assert should_send_sms("5551234567", True, sms_service_enabled=True) is True
        assert should_send_sms("5551234567", True, sms_service_enabled=False) is False
        assert should_send_sms("5551234567", False, sms_service_enabled=True) is False


class TestChooseNotificationChannel:
    def test_sms_when_college_enables_sms(self, test_user, test_college):
        test_college.sms_enabled = True
        assert choose_notification_channel(test_user, test_college) == "sms"

    def test_email_when_college_sms_disabled(self, test_user, test_college):
        assert test_user.phone
        test_college.sms_enabled = False
        assert choose_notification_channel(test_user, test_college) == "email"

    def test_email_when_sms_service_disabled(self, test_user, test_college):
        test_college.sms_enabled = True
        assert (
            choose_notification_channel(
                test_user, test_college, sms_service_enabled=False
            )
            == "email"
        )
