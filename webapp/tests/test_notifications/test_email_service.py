"""Tests for email notification service."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from botocore.exceptions import ClientError

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from notifications.email_service import EmailService


@pytest.fixture
def mock_ses_client():
    """Create a mock AWS SES client."""
    with patch("notifications.email_service.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_jinja_env():
    """Create a mock Jinja2 environment."""
    with patch("notifications.email_service.Environment") as mock_env_class:
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Test email</html>"
        mock_env.get_template.return_value = mock_template
        mock_env_class.return_value = mock_env
        yield mock_env


class TestEmailServiceInit:
    """Tests for EmailService initialization."""

    @pytest.mark.unit
    def test_init_with_ses_enabled(self, mock_ses_client, mock_jinja_env):
        """Test initialization when AWS SES is enabled."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "test@example.com"
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.AWS_ACCESS_KEY_ID = "test_key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test_secret"

            service = EmailService()

            assert service.is_enabled is True
            assert service.from_email == "test@example.com"

    @pytest.mark.unit
    def test_init_with_ses_disabled(self, mock_jinja_env):
        """Test initialization when AWS SES is disabled."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = False

            service = EmailService()

            assert service.is_enabled is False
            assert service.ses_client is None


class TestSendMagicLink:
    """Tests for send_magic_link method."""

    @pytest.mark.unit
    async def test_send_magic_link_success(self, mock_ses_client, mock_jinja_env):
        """Test successful magic link email sending."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"

            mock_ses_client.send_email.return_value = {"MessageId": "test-message-id"}

            service = EmailService()
            result = await service.send_magic_link(
                "user@example.com", "https://example.com/auth?token=abc123"
            )

            assert result is True
            mock_ses_client.send_email.assert_called_once()

            # Verify email structure
            call_args = mock_ses_client.send_email.call_args[1]
            assert call_args["Source"] == "noreply@example.com"
            assert call_args["Destination"]["ToAddresses"] == ["user@example.com"]
            assert "Sign in to SeatSteal" in call_args["Message"]["Subject"]["Data"]

    @pytest.mark.unit
    async def test_send_magic_link_disabled_service(self, mock_jinja_env):
        """Test magic link sending when service is disabled."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = False

            service = EmailService()
            result = await service.send_magic_link(
                "user@example.com", "https://example.com/auth?token=abc123"
            )

            assert result is False

    @pytest.mark.unit
    async def test_send_magic_link_client_error(self, mock_ses_client, mock_jinja_env):
        """Test magic link sending with SES client error."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"

            # Simulate SES error
            mock_ses_client.send_email.side_effect = ClientError(
                {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
                "SendEmail",
            )

            service = EmailService()
            result = await service.send_magic_link(
                "user@example.com", "https://example.com/auth?token=abc123"
            )

            assert result is False

    @pytest.mark.unit
    async def test_send_magic_link_template_renders_correctly(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test that magic link template renders with correct variables."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"

            mock_template = MagicMock()
            mock_jinja_env.get_template.return_value = mock_template

            mock_ses_client.send_email.return_value = {"MessageId": "test-id"}

            service = EmailService()
            await service.send_magic_link(
                "user@example.com", "https://example.com/auth?token=abc123"
            )

            # Verify template was called with correct context
            mock_template.render.assert_called_once()
            render_args = mock_template.render.call_args[1]
            assert render_args["magic_link"] == "https://example.com/auth?token=abc123"
            assert render_args["email"] == "user@example.com"
            assert render_args["app_name"] == "SeatSteal"


class TestSendCourseNotification:
    """Tests for send_course_notification method."""

    @pytest.mark.unit
    async def test_send_course_notification_success(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test successful course notification sending."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"
            mock_settings.effective_frontend_url = "https://app.example.com"

            mock_ses_client.send_email.return_value = {"MessageId": "notif-123"}

            service = EmailService()
            result = await service.send_course_notification(
                to_email="student@example.com",
                course_code="CS 101",
                course_title="Intro to Computer Science",
                class_section="A1",
                college_name="Test University",
            )

            assert result is True
            mock_ses_client.send_email.assert_called_once()

            # Verify email content
            call_args = mock_ses_client.send_email.call_args[1]
            assert "Seat available" in call_args["Message"]["Subject"]["Data"]
            assert "Intro to Computer Science" in call_args["Message"]["Subject"]["Data"]

    @pytest.mark.unit
    async def test_send_course_notification_with_unsubscribe(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test course notification includes unsubscribe link."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"
            mock_settings.effective_frontend_url = "https://app.example.com"

            mock_template = MagicMock()
            mock_jinja_env.get_template.return_value = mock_template

            mock_ses_client.send_email.return_value = {"MessageId": "notif-123"}

            service = EmailService()
            await service.send_course_notification(
                to_email="student@example.com",
                course_code="CS 101",
                course_title="Intro to Computer Science",
                class_section="A1",
                college_name="Test University",
                unsubscribe_url="https://app.example.com/unsubscribe/123",
            )

            # Verify unsubscribe URL was passed to template
            render_args = mock_template.render.call_args[1]
            assert (
                render_args["unsubscribe_url"]
                == "https://app.example.com/unsubscribe/123"
            )

    @pytest.mark.unit
    async def test_send_course_notification_includes_plaintext(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test that course notification includes plain text version."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"
            mock_settings.effective_frontend_url = "https://app.example.com"

            mock_ses_client.send_email.return_value = {"MessageId": "notif-123"}

            service = EmailService()
            await service.send_course_notification(
                to_email="student@example.com",
                course_code="CS 101",
                course_title="Intro to Computer Science",
                class_section="A1",
                college_name="Test University",
            )

            call_args = mock_ses_client.send_email.call_args[1]
            text_body = call_args["Message"]["Body"]["Text"]["Data"]

            assert "CS 101" in text_body
            assert "Intro to Computer Science" in text_body
            assert "A1" in text_body
            assert "Test University" in text_body


class TestSendBatchNotifications:
    """Tests for send_batch_notifications method."""

    @pytest.mark.unit
    async def test_send_batch_notifications_success(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test successful batch notification sending."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"
            mock_settings.effective_frontend_url = "https://app.example.com"

            mock_ses_client.send_email.return_value = {"MessageId": "batch-123"}

            notifications = [
                {
                    "to_email": "user1@example.com",
                    "course_code": "CS 101",
                    "course_title": "Intro to CS",
                    "class_section": "A1",
                    "college_name": "Test U",
                },
                {
                    "to_email": "user2@example.com",
                    "course_code": "CS 102",
                    "course_title": "Data Structures",
                    "class_section": "B1",
                    "college_name": "Test U",
                },
            ]

            service = EmailService()
            result = await service.send_batch_notifications(notifications)

            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert mock_ses_client.send_email.call_count == 2

    @pytest.mark.unit
    async def test_send_batch_notifications_partial_failure(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test batch notifications with partial failures."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"
            mock_settings.effective_frontend_url = "https://app.example.com"

            # First succeeds, second fails
            mock_ses_client.send_email.side_effect = [
                {"MessageId": "success-1"},
                ClientError({"Error": {"Code": "Throttling"}}, "SendEmail"),
            ]

            notifications = [
                {
                    "to_email": "user1@example.com",
                    "course_code": "CS 101",
                    "course_title": "Intro to CS",
                    "class_section": "A1",
                    "college_name": "Test U",
                },
                {
                    "to_email": "user2@example.com",
                    "course_code": "CS 102",
                    "course_title": "Data Structures",
                    "class_section": "B1",
                    "college_name": "Test U",
                },
            ]

            service = EmailService()
            result = await service.send_batch_notifications(notifications)

            assert result["total"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1

    @pytest.mark.unit
    async def test_send_batch_notifications_disabled_service(self, mock_jinja_env):
        """Test batch notifications when service is disabled."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = False

            notifications = [
                {
                    "to_email": "user1@example.com",
                    "course_code": "CS 101",
                    "course_title": "Intro to CS",
                    "class_section": "A1",
                    "college_name": "Test U",
                }
            ]

            service = EmailService()
            result = await service.send_batch_notifications(notifications)

            assert result["total"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 1


class TestSendSubscriptionConfirmation:
    """Tests for send_subscription_confirmation method."""

    @pytest.mark.unit
    async def test_send_subscription_confirmation_success(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test successful subscription confirmation sending."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"

            mock_ses_client.send_email.return_value = {"MessageId": "confirm-123"}

            service = EmailService()
            result = await service.send_subscription_confirmation(
                to_email="student@example.com",
                course_code="CS 101",
                course_title="Intro to CS",
                college_name="Test University",
            )

            assert result is True
            mock_ses_client.send_email.assert_called_once()

            # Verify subject line
            call_args = mock_ses_client.send_email.call_args[1]
            assert "Watching CS 101" in call_args["Message"]["Subject"]["Data"]

    @pytest.mark.unit
    async def test_send_subscription_confirmation_error(
        self, mock_ses_client, mock_jinja_env
    ):
        """Test subscription confirmation with error."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True
            mock_settings.AWS_SES_FROM_EMAIL = "noreply@example.com"

            mock_ses_client.send_email.side_effect = Exception("SES error")

            service = EmailService()
            result = await service.send_subscription_confirmation(
                to_email="student@example.com",
                course_code="CS 101",
                course_title="Intro to CS",
                college_name="Test University",
            )

            assert result is False


class TestVerifyEmailAddress:
    """Tests for verify_email_address method."""

    @pytest.mark.unit
    def test_verify_email_success(self, mock_ses_client, mock_jinja_env):
        """Test successful email verification."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True

            service = EmailService()
            result = service.verify_email_address("test@example.com")

            assert result is True
            mock_ses_client.verify_email_identity.assert_called_once_with(
                EmailAddress="test@example.com"
            )

    @pytest.mark.unit
    def test_verify_email_disabled_service(self, mock_jinja_env):
        """Test email verification when service is disabled."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = False

            service = EmailService()
            result = service.verify_email_address("test@example.com")

            assert result is False

    @pytest.mark.unit
    def test_verify_email_client_error(self, mock_ses_client, mock_jinja_env):
        """Test email verification with client error."""
        with patch("notifications.email_service.settings") as mock_settings:
            mock_settings.aws_ses_enabled = True

            mock_ses_client.verify_email_identity.side_effect = ClientError(
                {"Error": {"Code": "InvalidEmail"}}, "VerifyEmailIdentity"
            )

            service = EmailService()
            result = service.verify_email_address("invalid@")

            assert result is False
