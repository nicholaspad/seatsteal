"""Shared SMS vs email decision used by seat alerts and waitlist recovery."""

from __future__ import annotations

from typing import Optional

from models.college import College
from models.user import Profile


def should_send_sms(
    phone: Optional[str],
    sms_enabled: bool,
    sms_service_enabled: bool = True,
) -> bool:
    """Return True when the seat-alert sender would send SMS.

    Seat alerts send SMS only when a phone is on file AND SMS is enabled
    (``College.sms_enabled`` for the school, plus a ready SMS service).
    Phone-on-file alone is not an SMS opt-in. Twilio being configured is
    not enough either — the school must also have SMS turned on.
    """
    return (
        bool((phone or "").strip()) and bool(sms_enabled) and bool(sms_service_enabled)
    )


def choose_notification_channel(
    user: Optional[Profile],
    college: Optional[College] = None,
    *,
    sms_service_enabled: bool = True,
) -> str:
    """SMS if the user is opted in the same way seat alerts are, else email."""
    phone = user.phone if user is not None else None
    college_sms_enabled = bool(college is not None and college.sms_enabled)
    if should_send_sms(
        phone,
        college_sms_enabled,
        sms_service_enabled=sms_service_enabled,
    ):
        return "sms"
    return "email"
