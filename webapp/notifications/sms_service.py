"""
SMS notification service using Twilio

Sends SMS notifications to users with phone numbers on file.
Messages are kept under 160 characters to fit within a single SMS segment.

Rate Limiting:
- Twilio sole proprietor accounts are limited to 1 message per second
- This service implements client-side rate limiting to stay within this limit
- Messages are queued and sent at a maximum rate of 1 per second
"""

import time
import threading
from collections import deque
from dataclasses import dataclass
from typing import Optional, Deque
from loguru import logger

from config import settings


@dataclass
class SMSMessage:
    """Represents an SMS message in the queue"""

    to_phone: str
    body: str


class SMSService:
    """Twilio SMS service for sending notifications with rate limiting

    Rate limiting is implemented to comply with Twilio sole proprietor
    throughput limits of 1 message per second.
    """

    # Maximum characters for a single SMS segment (GSM-7 encoding)
    MAX_SMS_LENGTH = 160

    # Rate limit: 1 message per second (Twilio sole proprietor limit)
    RATE_LIMIT_INTERVAL = 1.0  # seconds between messages

    def __init__(self):
        """Initialize Twilio client if configured"""
        self.client = None
        self.from_number = settings.TWILIO_FROM_NUMBER

        # Rate limiting state
        self._last_send_time: float = 0.0
        self._rate_limit_lock = threading.Lock()

        # Message queue for batch processing
        self._message_queue: Deque[SMSMessage] = deque()

        if settings.twilio_enabled:
            try:
                from twilio.rest import Client

                self.client = Client(
                    settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
                )
                logger.info(
                    f"SMSService initialized with from number: {self.from_number}"
                )
                logger.info(
                    f"SMS rate limiting enabled: {self.RATE_LIMIT_INTERVAL}s between messages"
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

    def _wait_for_rate_limit(self) -> float:
        """
        Wait if necessary to comply with rate limiting.

        This method is thread-safe: it acquires a lock, waits if needed,
        and reserves the current time slot before releasing the lock.
        This prevents race conditions where multiple threads could
        bypass the rate limit.

        Returns:
            The time waited in seconds (0 if no wait was needed)
        """
        with self._rate_limit_lock:
            current_time = time.time()
            time_since_last_send = current_time - self._last_send_time
            wait_time = self.RATE_LIMIT_INTERVAL - time_since_last_send

            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.3f}s before next SMS")
                time.sleep(wait_time)

            # Reserve this time slot immediately to prevent race conditions
            # Even if the send fails, we've consumed the rate limit slot
            self._last_send_time = time.time()

            return max(wait_time, 0.0)

    def _send_raw(self, to_phone: str, body: str) -> bool:
        """
        Send an SMS message directly via Twilio (internal use).

        This method does NOT apply rate limiting - use send_course_notification
        or queue methods for rate-limited sending.

        Args:
            to_phone: Recipient phone number in E.164 format
            body: Message body

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            result = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_phone,
            )
            logger.info(f"SMS sent to {to_phone}: SID={result.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return False

    def send_course_notification(
        self,
        to_phone: str,
        course_name: str,
        section_code: str,
        college_name: str,
    ) -> bool:
        """
        Send course availability SMS notification with rate limiting.

        Message is kept under 160 characters to fit in one SMS segment.
        This method applies rate limiting (1 message per second) to comply
        with Twilio sole proprietor throughput limits.

        Args:
            to_phone: Recipient phone number (E.164 format, e.g., +15551234567)
            course_name: Course name/title (e.g., 'Introduction to Computer Science')
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
            course_name, section_code, college_name
        )

        # Apply rate limiting before sending (also reserves the time slot)
        wait_time = self._wait_for_rate_limit()
        if wait_time > 0:
            logger.info(f"Rate limited: waited {wait_time:.2f}s before sending SMS")

        # Send the message
        success = self._send_raw(normalized_phone, message)

        if success:
            logger.info(f"SMS sent to {normalized_phone} for {course_name}")

        return success

    def queue_course_notification(
        self,
        to_phone: str,
        course_name: str,
        section_code: str,
        college_name: str,
    ) -> bool:
        """
        Queue a course notification SMS for later batch sending.

        Use this method when you want to queue multiple SMS messages
        and then send them all at once with flush_queue().

        Args:
            to_phone: Recipient phone number (E.164 format)
            course_name: Course name/title
            section_code: Section identifier
            college_name: Name of the college

        Returns:
            True if message was queued successfully, False otherwise
        """
        if not to_phone:
            logger.warning("No phone number provided, skipping queue")
            return False

        normalized_phone = self._normalize_phone(to_phone)
        if not normalized_phone:
            logger.warning(f"Invalid phone number format: {to_phone}")
            return False

        message = self._build_notification_message(
            course_name, section_code, college_name
        )

        self._message_queue.append(SMSMessage(to_phone=normalized_phone, body=message))
        logger.debug(
            f"Queued SMS for {normalized_phone}, queue size: {len(self._message_queue)}"
        )
        return True

    def flush_queue(self) -> dict:
        """
        Send all queued SMS messages with rate limiting.

        Messages are sent at a maximum rate of 1 per second to comply
        with Twilio sole proprietor throughput limits.

        Returns:
            Dict with 'sent', 'failed', and 'total' counts
        """
        if not self.is_enabled:
            queue_size = len(self._message_queue)
            self._message_queue.clear()
            logger.warning(
                f"SMS service not enabled, discarding {queue_size} queued messages"
            )
            return {"sent": 0, "failed": queue_size, "total": queue_size}

        sent = 0
        failed = 0
        total = len(self._message_queue)

        if total == 0:
            return {"sent": 0, "failed": 0, "total": 0}

        logger.info(f"Flushing SMS queue: {total} messages to send at 1/second")
        start_time = time.time()

        while self._message_queue:
            msg = self._message_queue.popleft()

            # Apply rate limiting (also reserves the time slot)
            self._wait_for_rate_limit()

            # Send the message
            if self._send_raw(msg.to_phone, msg.body):
                sent += 1
            else:
                failed += 1

        elapsed = time.time() - start_time
        logger.info(
            f"SMS queue flushed: {sent}/{total} sent, {failed} failed in {elapsed:.1f}s"
        )

        return {"sent": sent, "failed": failed, "total": total}

    @property
    def queue_size(self) -> int:
        """Return the current size of the message queue"""
        return len(self._message_queue)

    def _build_notification_message(
        self, course_name: str, section_code: str, college_name: str
    ) -> str:
        """
        Build SMS message that fits within one segment (160 chars).

        Template: "SeatSteal: {course} {section} at {college} is OPEN!"
        Course name is truncated if needed to fit within the limit.
        College name and section code are never truncated.
        """
        # Base template structure:
        # "SeatSteal: " = 11 chars
        # " " (space before section) = 1 char
        # " at " = 4 chars
        # " is OPEN!" = 9 chars
        # Total overhead: 25 chars

        base_prefix = "SeatSteal: "
        base_suffix = " is OPEN!"

        # Calculate space available for course name
        # Section and college are kept intact
        section_part = f" {section_code}"
        college_part = f" at {college_name}"
        fixed_overhead = (
            len(base_prefix) + len(section_part) + len(college_part) + len(base_suffix)
        )
        available_for_course = self.MAX_SMS_LENGTH - fixed_overhead

        # Truncate course name if needed
        if len(course_name) > available_for_course:
            course_name = course_name[: available_for_course - 3] + "..."

        message = f"{base_prefix}{course_name}{section_part}{college_part}{base_suffix}"

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
