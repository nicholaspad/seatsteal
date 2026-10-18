"""College seat-data waitlist signup, admin counts, and recovery notify.

Recovery is a lightweight periodic check (see ``send_notifs.NotificationJob``),
not the scraper write path. The notify function is idempotent (``notified_at``),
batch-limited, and never deletes rows. Failures increment ``attempts`` and
are retried on the next pass until ``MAX_WAITLIST_ATTEMPTS``.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from models.college import College
from models.college_data_waitlist import CollegeDataWaitlist
from models.user import Profile
from notifications.channel import choose_notification_channel
from utils.college_data_status import get_colleges_data_status

WaitlistChannel = Literal["sms", "email"]

DEFAULT_NOTIFY_BATCH_LIMIT = 100
WAITLIST_RATE_LIMIT = 8
WAITLIST_RATE_WINDOW_SECONDS = 600
WAITLIST_SEND_TIMEOUT_SECONDS = 30.0
MAX_WAITLIST_ATTEMPTS = 5

_rate_hits: dict[str, list[float]] = {}


def college_course_search_url(college_id: int) -> str:
    """Frontend college-filtered course search, using effective_frontend_url."""
    return f"{settings.effective_frontend_url.rstrip('/')}/courses?college={college_id}"


def recovery_notification_text(college_name: str, college_id: int) -> str:
    """Exact email/SMS recovery copy: school name + course-search link."""
    return (
        f"{college_name} seat data is back. "
        f"Set your alerts: {college_course_search_url(college_id)}"
    )


def reset_waitlist_rate_limiter() -> None:
    """Clear in-process rate-limit state (tests)."""
    _rate_hits.clear()


def waitlist_rate_limited(ip: str, college_id: int) -> bool:
    """Return True if this IP has hit the waitlist endpoint too often."""
    key = f"{ip}:{college_id}"
    now = time.time()
    hits = [
        t for t in _rate_hits.get(key, []) if now - t < WAITLIST_RATE_WINDOW_SECONDS
    ]
    if len(hits) >= WAITLIST_RATE_LIMIT:
        _rate_hits[key] = hits
        return True
    hits.append(now)
    _rate_hits[key] = hits
    return False


def normalize_waitlist_email(email: Optional[str]) -> Optional[str]:
    if email is None:
        return None
    cleaned = email.strip()
    return cleaned.lower() if cleaned else None


def choose_waitlist_channel(
    user: Optional[Profile],
    college: Optional[College] = None,
    *,
    sms_service_enabled: bool = True,
) -> WaitlistChannel:
    """Same SMS-vs-email gate as seat alerts: phone AND college.sms_enabled."""
    return choose_notification_channel(
        user,
        college,
        sms_service_enabled=sms_service_enabled,
    )


def find_existing_waitlist_row(
    db: Session,
    college_id: int,
    *,
    user_id: Optional[UUID] = None,
    email: Optional[str] = None,
) -> Optional[CollegeDataWaitlist]:
    if user_id is not None:
        row = db.execute(
            select(CollegeDataWaitlist).where(
                CollegeDataWaitlist.college_id == college_id,
                CollegeDataWaitlist.user_id == user_id,
            )
        ).scalar_one_or_none()
        if row is not None:
            return row

    normalized = normalize_waitlist_email(email)
    if normalized:
        return db.execute(
            select(CollegeDataWaitlist).where(
                CollegeDataWaitlist.college_id == college_id,
                func.lower(CollegeDataWaitlist.email) == normalized,
            )
        ).scalar_one_or_none()
    return None


def register_waitlist(
    db: Session,
    college_id: int,
    *,
    user: Optional[Profile] = None,
    email: Optional[str] = None,
) -> CollegeDataWaitlist:
    """Insert or return the existing waitlist row. Never deletes."""
    stored_email = (
        normalize_waitlist_email(user.email)
        if user is not None
        else normalize_waitlist_email(email)
    )
    user_id = user.id if user is not None else None

    existing = find_existing_waitlist_row(
        db, college_id, user_id=user_id, email=stored_email
    )
    if existing is not None:
        return existing

    row = CollegeDataWaitlist(
        college_id=college_id,
        user_id=user_id,
        email=stored_email,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        existing = find_existing_waitlist_row(
            db, college_id, user_id=user_id, email=stored_email
        )
        if existing is not None:
            return existing
        raise


def get_waitlist_counts_by_college(db: Session) -> list[dict[str, Any]]:
    """Per-school signup counts for admin: total / signed-in / email-only / pending."""
    signed_in = func.count(case((CollegeDataWaitlist.user_id.is_not(None), 1)))
    email_only = func.count(
        case(
            (
                (CollegeDataWaitlist.user_id.is_(None))
                & (CollegeDataWaitlist.email.is_not(None)),
                1,
            )
        )
    )
    not_yet_notified = func.count(case((CollegeDataWaitlist.notified_at.is_(None), 1)))

    rows = db.execute(
        select(
            College.id.label("college_id"),
            College.name.label("college_name"),
            College.short_name.label("short_name"),
            func.count(CollegeDataWaitlist.id).label("total"),
            signed_in.label("signed_in"),
            email_only.label("email_only"),
            not_yet_notified.label("not_yet_notified"),
        )
        .select_from(CollegeDataWaitlist)
        .join(College, College.id == CollegeDataWaitlist.college_id)
        .group_by(College.id, College.name, College.short_name)
        .order_by(College.name)
    ).all()

    return [
        {
            "collegeId": row.college_id,
            "collegeName": row.college_name,
            "shortName": row.short_name,
            "total": row.total,
            "signedIn": row.signed_in,
            "emailOnly": row.email_only,
            "notYetNotified": row.not_yet_notified,
        }
        for row in rows
    ]


async def _await_send_result(result: Any) -> Any:
    if asyncio.iscoroutine(result):
        return await result
    return result


def _call_maybe_async(fn, *args, **kwargs) -> bool:
    """Run a sync or async send with the same 30s timeout seat alerts use."""
    try:
        return bool(
            asyncio.run(
                asyncio.wait_for(
                    _await_send_result(fn(*args, **kwargs)),
                    timeout=WAITLIST_SEND_TIMEOUT_SECONDS,
                )
            )
        )
    except asyncio.TimeoutError:
        logger.error(
            "Waitlist send timed out after {}s",
            WAITLIST_SEND_TIMEOUT_SECONDS,
        )
        return False


def _send_waitlist_email(
    email_service: Any, to_email: str, college_name: str, college_id: int
) -> bool:
    send = getattr(email_service, "send_data_restored_notification", None)
    if send is None:
        logger.error("Email service missing send_data_restored_notification")
        return False
    return _call_maybe_async(send, to_email, college_name, college_id)


def _send_waitlist_sms(
    sms_service: Any, to_phone: str, college_name: str, college_id: int
) -> bool:
    send = getattr(sms_service, "send_data_restored_notification", None)
    if send is None:
        logger.error("SMS service missing send_data_restored_notification")
        return False
    return _call_maybe_async(send, to_phone, college_name, college_id)


def notify_recovered_college_waitlists(
    db: Session,
    *,
    college_id: Optional[int] = None,
    batch_limit: int = DEFAULT_NOTIFY_BATCH_LIMIT,
    dry_run: bool = False,
    email_service: Any = None,
    sms_service: Any = None,
    now: Optional[datetime] = None,
) -> dict[str, int]:
    """Send one-time recovery notices for colleges whose dataStatus is ok.

    Only active colleges are notified (inactive schools always report ok
    and are not a 'data is back' event). Failures increment ``attempts``
    and leave ``notified_at`` null so the next periodic pass retries,
    up to ``MAX_WAITLIST_ATTEMPTS``. Rows are never deleted.
    """
    from notifications.email_service import EmailService
    from notifications.sms_service import SMSService

    if batch_limit <= 0:
        return {"examined": 0, "sent": 0, "failed": 0, "skipped": 0}

    now_utc = now or datetime.now(timezone.utc)
    pending_filter = [
        CollegeDataWaitlist.notified_at.is_(None),
        CollegeDataWaitlist.attempts < MAX_WAITLIST_ATTEMPTS,
    ]
    if college_id is not None:
        pending_filter.append(CollegeDataWaitlist.college_id == college_id)

    pending_college_ids = list(
        db.execute(
            select(CollegeDataWaitlist.college_id).where(*pending_filter).distinct()
        ).scalars()
    )
    if not pending_college_ids:
        return {"examined": 0, "sent": 0, "failed": 0, "skipped": 0}

    colleges = (
        db.execute(select(College).where(College.id.in_(pending_college_ids)))
        .scalars()
        .all()
    )
    status_map = get_colleges_data_status(db, colleges, now=now_utc)
    recovered_ids = [
        college.id
        for college in colleges
        if college.is_active
        and status_map.get(college.id) is not None
        and status_map[college.id].data_status == "ok"
    ]
    if not recovered_ids:
        return {"examined": 0, "sent": 0, "failed": 0, "skipped": 0}

    # Filter attempts in SQL so exhausted rows cannot fill the
    # oldest-first LIMIT and starve newer signups.
    pending_rows = (
        db.execute(
            select(CollegeDataWaitlist)
            .where(
                CollegeDataWaitlist.college_id.in_(recovered_ids),
                CollegeDataWaitlist.notified_at.is_(None),
                CollegeDataWaitlist.attempts < MAX_WAITLIST_ATTEMPTS,
            )
            .order_by(CollegeDataWaitlist.created_at, CollegeDataWaitlist.id)
            .limit(batch_limit)
        )
        .scalars()
        .all()
    )
    if not pending_rows:
        return {"examined": 0, "sent": 0, "failed": 0, "skipped": 0}

    college_by_id = {college.id: college for college in colleges}
    user_ids = [row.user_id for row in pending_rows if row.user_id is not None]
    users_by_id: dict[UUID, Profile] = {}
    if user_ids:
        users_by_id = {
            user.id: user
            for user in db.execute(
                select(Profile).where(Profile.id.in_(user_ids))
            ).scalars()
        }

    if email_service is None:
        email_service = EmailService()
    if sms_service is None:
        sms_service = SMSService()

    sent = 0
    failed = 0
    skipped = 0

    for row in pending_rows:
        college = college_by_id.get(row.college_id)
        if college is None:
            skipped += 1
            continue

        user = users_by_id.get(row.user_id) if row.user_id else None
        channel = choose_waitlist_channel(
            user,
            college,
            sms_service_enabled=bool(getattr(sms_service, "is_enabled", True)),
        )
        destination_email = (
            normalize_waitlist_email(user.email)
            if user is not None
            else normalize_waitlist_email(row.email)
        )

        if dry_run:
            logger.info(
                "DRY RUN: would notify waitlist row {} for {} via {}",
                row.id,
                college.name,
                channel,
            )
            skipped += 1
            continue

        success = False
        try:
            if channel == "sms" and user is not None and (user.phone or "").strip():
                success = _send_waitlist_sms(
                    sms_service, user.phone, college.name, college.id
                )
            elif destination_email:
                success = _send_waitlist_email(
                    email_service, destination_email, college.name, college.id
                )
            else:
                logger.error("Waitlist row {} has no deliverable address", row.id)
        except Exception as exc:
            logger.error("Waitlist notify failed for row {}: {}", row.id, exc)
            success = False

        if success:
            row.notified_at = now_utc
            db.add(row)
            db.commit()
            sent += 1
        else:
            row.attempts = (row.attempts or 0) + 1
            row.last_attempt_at = now_utc
            db.add(row)
            db.commit()
            failed += 1
            if row.attempts >= MAX_WAITLIST_ATTEMPTS:
                logger.error(
                    "Waitlist row {} exhausted {} attempts; giving up",
                    row.id,
                    MAX_WAITLIST_ATTEMPTS,
                )
            else:
                logger.error(
                    "Waitlist notify unsuccessful for row {} ({}); will retry",
                    row.id,
                    channel,
                )

    return {
        "examined": len(pending_rows),
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
    }
