import boto3
from botocore.exceptions import ClientError
from jinja2 import Template, Environment, FileSystemLoader
from pathlib import Path
from loguru import logger
from typing import List, Optional

from ..config import settings


class EmailService:
    """AWS SES email service for sending notifications and auth emails"""

    def __init__(self):
        """Initialize AWS SES client and load email templates"""
        self.ses_client = boto3.client(
            "ses",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.from_email = settings.AWS_SES_FROM_EMAIL

        # Set up Jinja2 template environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

        logger.info(f"EmailService initialized with sender: {self.from_email}")

    async def send_magic_link(self, to_email: str, magic_link: str) -> bool:
        """
        Send magic link authentication email.

        Args:
            to_email: Recipient email address
            magic_link: Authentication magic link URL

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            template = self.jinja_env.get_template("magic_link.html")
            html_body = template.render(
                magic_link=magic_link, email=to_email, app_name="SeatSteal"
            )

            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": "Sign in to SeatSteal", "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {
                            "Data": f"Click here to sign in: {magic_link}",
                            "Charset": "UTF-8",
                        },
                    },
                },
            )

            message_id = response["MessageId"]
            logger.info(f"Sent magic link to {to_email}: {message_id}")
            return True

        except ClientError as e:
            logger.error(f"Failed to send magic link to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending magic link to {to_email}: {e}")
            return False

    async def send_course_notification(
        self,
        to_email: str,
        course_code: str,
        course_title: str,
        class_section: str,
        spots_available: int,
        college_name: str,
        unsubscribe_url: Optional[str] = None,
    ) -> bool:
        """
        Send course availability notification email.

        Args:
            to_email: Recipient email address
            course_code: Course code (e.g., 'CS 101')
            course_title: Course title
            class_section: Section identifier
            spots_available: Number of available spots
            college_name: Name of the college
            unsubscribe_url: Optional unsubscribe link

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            template = self.jinja_env.get_template("course_notification.html")
            html_body = template.render(
                course_code=course_code,
                course_title=course_title,
                class_section=class_section,
                spots_available=spots_available,
                college_name=college_name,
                course_url=f"{settings.FRONTEND_URL}/courses/{course_code}",
                unsubscribe_url=unsubscribe_url,
                app_name="SeatSteal",
            )

            subject = f"🎉 Seat available in {course_code}!"

            # Plain text fallback
            text_body = f"""
A seat is now available in your watched course!

{course_code}: {course_title}
Section: {class_section}
College: {college_name}
Spots available: {spots_available}

Act fast before it fills up!

View course: {settings.FRONTEND_URL}/courses/{course_code}
"""

            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                },
            )

            message_id = response["MessageId"]
            logger.info(
                f"Sent notification to {to_email} for {course_code}: {message_id}"
            )
            return True

        except ClientError as e:
            logger.error(f"Failed to send notification to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending notification to {to_email}: {e}")
            return False

    async def send_batch_notifications(self, notifications: List[dict]) -> dict:
        """
        Send multiple notifications in batch (more efficient for large volumes).

        Args:
            notifications: List of notification dicts with keys:
                - to_email
                - course_code
                - course_title
                - class_section
                - spots_available
                - college_name

        Returns:
            Dict with success/failure counts
        """
        successful = 0
        failed = 0

        for notification in notifications:
            success = await self.send_course_notification(
                to_email=notification["to_email"],
                course_code=notification["course_code"],
                course_title=notification["course_title"],
                class_section=notification["class_section"],
                spots_available=notification["spots_available"],
                college_name=notification["college_name"],
                unsubscribe_url=notification.get("unsubscribe_url"),
            )

            if success:
                successful += 1
            else:
                failed += 1

        logger.info(f"Batch notifications complete: {successful} sent, {failed} failed")

        return {"total": len(notifications), "successful": successful, "failed": failed}

    async def send_subscription_confirmation(
        self, to_email: str, course_code: str, course_title: str, college_name: str
    ) -> bool:
        """
        Send subscription confirmation email.

        Args:
            to_email: Recipient email address
            course_code: Course code
            course_title: Course title
            college_name: College name

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = f"✅ Watching {course_code}"

            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2>You're now watching this course!</h2>
    <p>You'll receive an email notification when a seat becomes available.</p>

    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <strong>{course_code}: {course_title}</strong><br>
        <span style="color: #666;">{college_name}</span>
    </div>

    <p>We'll check for availability regularly and notify you as soon as a spot opens up.</p>

    <p style="font-size: 12px; color: #999; margin-top: 30px;">
        SeatSteal - Never miss a course opening
    </p>
</body>
</html>
"""

            text_body = f"""
You're now watching {course_code}: {course_title} at {college_name}!

You'll receive an email notification when a seat becomes available.

SeatSteal
"""

            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                },
            )

            logger.info(
                f"Sent subscription confirmation to {to_email}: {response['MessageId']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send confirmation to {to_email}: {e}")
            return False

    def verify_email_address(self, email: str) -> bool:
        """
        Verify an email address with AWS SES (required for sandbox mode).

        Args:
            email: Email address to verify

        Returns:
            True if verification initiated successfully
        """
        try:
            self.ses_client.verify_email_identity(EmailAddress=email)
            logger.info(f"Verification email sent to {email}")
            return True
        except ClientError as e:
            logger.error(f"Failed to verify email {email}: {e}")
            return False
