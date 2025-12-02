"""
SMS notification service using Twilio

Sends SMS notifications to users with phone numbers on file.
Messages are kept under 160 characters to fit within a single SMS segment.
"""

from loguru import logger
from typing import Optional

from config import settings


class SMSService:
    """Twilio SMS service for sending notifications"""

    # Maximum characters for a single SMS segment (GSM-7 encoding)
    MAX_SMS_LENGTH = 160

    def __init__(self):
        """Initialize Twilio client if configured"""
        self.client = None
        self.from_number = settings.TWILIO_FROM_NUMBER

        if settings.twilio_enabled:
            try:
                from twilio.rest import Client

                self.client = Client(
                    settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
                )
                logger.info(
                    f"SMSService initialized with from number: {self.from_number}"
                )
            except ImportError:
                logger.warning("Twilio SDK not installed, SMS notifications disabled")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        else:
            logger.info("Twilio not configured, SMS notifications disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if SMS service is properly configured and ready"""
        return self.client is not None

    def send_course_notification(
        self,
        to_phone: str,
        course_code: str,
        section_code: str,
        college_name: str,
    ) -> bool:
        """
        Send course availability SMS notification.

        Message is kept under 160 characters to fit in one SMS segment.

        Args:
            to_phone: Recipient phone number (E.164 format, e.g., +15551234567)
            course_code: Course code (e.g., 'CS 101')
            section_code: Section identifier
            college_name: Name of the college

        Returns:
            True if SMS sent successfully, False otherwise
        """
        if not self.is_enabled:
            logger.warning("SMS service not enabled, skipping SMS notification")
            return False

        if not to_phone:
            logger.warning("No phone number provided, skipping SMS")
            return False

        # Normalize phone number to E.164 format if needed
        normalized_phone = self._normalize_phone(to_phone)
        if not normalized_phone:
            logger.warning(f"Invalid phone number format: {to_phone}")
            return False

        # Build message that fits in one SMS segment (160 chars)
        message = self._build_notification_message(
            course_code, section_code, college_name
        )

        try:
            result = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=normalized_phone,
            )

            logger.info(
                f"SMS sent to {normalized_phone} for {course_code}: SID={result.sid}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {normalized_phone}: {e}")
            return False

    def _build_notification_message(
        self, course_code: str, section_code: str, college_name: str
    ) -> str:
        """
        Build SMS message that fits within one segment (160 chars).

        Template: "SeatSteal: {course} {section} at {college} is OPEN! Register now."
        If too long, truncates college name with ellipsis.
        """
        # Base template with placeholders
        # "SeatSteal: " = 11 chars
        # " at " = 4 chars
        # " is OPEN! Register now." = 23 chars
        # Total overhead: 38 chars
        # Available for course+section+college: 122 chars

        base_prefix = "SeatSteal: "
        course_section = f"{course_code} {section_code}"
        base_suffix = " is OPEN! Register now."

        # Calculate available space for college name
        fixed_length = (
            len(base_prefix) + len(course_section) + len(" at ") + len(base_suffix)
        )
        available_for_college = self.MAX_SMS_LENGTH - fixed_length

        # Truncate college name if needed
        if len(college_name) > available_for_college:
            college_name = college_name[: available_for_college - 3] + "..."

        message = f"{base_prefix}{course_section} at {college_name}{base_suffix}"

        # Final safety check - truncate if still too long
        if len(message) > self.MAX_SMS_LENGTH:
            message = message[: self.MAX_SMS_LENGTH - 3] + "..."

        return message

    def _normalize_phone(self, phone: str) -> Optional[str]:
        """
        Normalize phone number to E.164 format.

        Args:
            phone: Phone number in various formats

        Returns:
            Normalized phone number in E.164 format, or None if invalid
        """
        if not phone:
            return None

        # Remove common formatting characters
        cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

        # If already in E.164 format (starts with +)
        if cleaned.startswith("+"):
            # Basic validation: should have at least 10 digits after +
            if len(cleaned) >= 11:
                return cleaned
            return None

        # Assume US number if 10 digits
        if len(cleaned) == 10:
            return f"+1{cleaned}"

        # Assume US number if 11 digits starting with 1
        if len(cleaned) == 11 and cleaned.startswith("1"):
            return f"+{cleaned}"

        # If more than 10 digits, assume it's a valid international number
        if len(cleaned) > 10:
            return f"+{cleaned}"

        return None
