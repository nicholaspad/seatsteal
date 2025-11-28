"""Push notification service using Firebase Cloud Messaging (FCM)"""

import os
from typing import List, Dict, Optional
from loguru import logger
import firebase_admin
from firebase_admin import credentials, messaging

from config import settings


class PushNotificationService:
    """Service for sending push notifications via Firebase Cloud Messaging"""

    _app = None
    _initialized = False

    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK with service account credentials"""
        if cls._initialized:
            return

        try:
            # Check if credentials file exists
            if not settings.FIREBASE_CREDENTIALS_PATH:
                logger.warning(
                    "FIREBASE_CREDENTIALS_PATH not set. Push notifications disabled."
                )
                return

            if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                logger.warning(
                    f"Firebase credentials file not found at {settings.FIREBASE_CREDENTIALS_PATH}. "
                    "Push notifications disabled."
                )
                return

            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            cls._app = firebase_admin.initialize_app(cred)
            cls._initialized = True
            logger.info("Firebase Cloud Messaging initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            cls._initialized = False

    @classmethod
    def is_available(cls) -> bool:
        """Check if push notifications are available"""
        return cls._initialized

    @classmethod
    def send_push_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Send a push notification to a single device.

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Optional custom data payload

        Returns:
            True if sent successfully, False otherwise
        """
        if not cls._initialized:
            cls.initialize()

        if not cls._initialized:
            logger.warning("Push notifications not available")
            return False

        try:
            # Construct the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
                apns=messaging.APNSConfig(
                    headers={"apns-priority": "10"},
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        ),
                    ),
                ),
            )

            # Send the message
            response = messaging.send(message)
            logger.info(f"Successfully sent push notification: {response}")
            return True

        except messaging.UnregisteredError:
            logger.warning(f"Device token is invalid or unregistered: {token[:20]}...")
            return False
        except messaging.SenderIdMismatchError:
            logger.error(f"Sender ID mismatch for token: {token[:20]}...")
            return False
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False

    @classmethod
    def send_batch_push_notifications(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, int]:
        """
        Send push notifications to multiple devices (batch).

        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Optional custom data payload

        Returns:
            Dict with success/failure counts: {"success": int, "failed": int}
        """
        if not cls._initialized:
            cls.initialize()

        if not cls._initialized:
            logger.warning("Push notifications not available")
            return {"success": 0, "failed": len(tokens)}

        if not tokens:
            return {"success": 0, "failed": 0}

        try:
            # Construct messages for all tokens
            messages = [
                messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data or {},
                    token=token,
                    apns=messaging.APNSConfig(
                        headers={"apns-priority": "10"},
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound="default",
                                badge=1,
                            ),
                        ),
                    ),
                )
                for token in tokens
            ]

            # Send batch (up to 500 messages at a time per FCM limit)
            batch_response = messaging.send_all(messages)

            logger.info(
                f"Batch push notification: {batch_response.success_count} successful, "
                f"{batch_response.failure_count} failed"
            )

            # Log individual failures for debugging
            if batch_response.failure_count > 0:
                for idx, response in enumerate(batch_response.responses):
                    if not response.success:
                        logger.warning(
                            f"Failed to send to token {tokens[idx][:20]}...: {response.exception}"
                        )

            return {
                "success": batch_response.success_count,
                "failed": batch_response.failure_count,
            }

        except Exception as e:
            logger.error(f"Failed to send batch push notifications: {e}")
            return {"success": 0, "failed": len(tokens)}

    @classmethod
    def send_course_notification(
        cls,
        token: str,
        course_code: str,
        section_code: str,
        college_name: str,
    ) -> bool:
        """
        Send a course availability notification.

        Args:
            token: FCM device token
            course_code: Course code (e.g., 'CS 101')
            section_code: Section identifier
            college_name: Name of the college

        Returns:
            True if sent successfully, False otherwise
        """
        title = f"🎉 Seat Available in {course_code}"
        body = f"Section {section_code} at {college_name} is now open!"

        data = {
            "type": "course_notification",
            "course_code": course_code,
            "section_code": section_code,
            "college_name": college_name,
        }

        return cls.send_push_notification(token, title, body, data)

    @classmethod
    def send_batch_course_notifications(
        cls,
        tokens: List[str],
        course_code: str,
        section_code: str,
        college_name: str,
    ) -> Dict[str, int]:
        """
        Send course availability notifications to multiple devices.

        Args:
            tokens: List of FCM device tokens
            course_code: Course code (e.g., 'CS 101')
            section_code: Section identifier
            college_name: Name of the college

        Returns:
            Dict with success/failure counts: {"success": int, "failed": int}
        """
        title = f"🎉 Seat Available in {course_code}"
        body = f"Section {section_code} at {college_name} is now open!"

        data = {
            "type": "course_notification",
            "course_code": course_code,
            "section_code": section_code,
            "college_name": college_name,
        }

        return cls.send_batch_push_notifications(tokens, title, body, data)

