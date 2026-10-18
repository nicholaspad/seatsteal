"""Tests for college data waitlist recovery notifications."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from models.college import College
from models.college_data_waitlist import CollegeDataWaitlist
from models.enrollment import Enrollment
from models.subscription import Subscription
from models.user import Profile
from utils.college_data_waitlist import (
    MAX_WAITLIST_ATTEMPTS,
    choose_waitlist_channel,
    college_course_search_url,
    notify_recovered_college_waitlists,
    recovery_notification_text,
    register_waitlist,
)


def _waitlist_row(
    college_id: int,
    *,
    user_id=None,
    email=None,
    notified_at=None,
    attempts=0,
    last_attempt_at=None,
    created_at=None,
) -> CollegeDataWaitlist:
    row = CollegeDataWaitlist(
        college_id=college_id,
        user_id=user_id,
        email=email,
        notified_at=notified_at,
        attempts=attempts,
        last_attempt_at=last_attempt_at,
    )
    if created_at is not None:
        row.created_at = created_at
    return row


class TestRecoveryNotificationCopy:
    def test_message_includes_school_name_and_course_search_link(
        self, test_college: College
    ):
        from config import settings

        alerts_url = college_course_search_url(test_college.id)
        message = recovery_notification_text(test_college.name, test_college.id)

        assert test_college.name in message
        assert alerts_url in message
        assert message == (
            f"{test_college.name} seat data is back. Set your alerts: {alerts_url}"
        )
        assert alerts_url == (
            f"{settings.effective_frontend_url.rstrip('/')}"
            f"/courses?college={test_college.id}"
        )


class TestChooseWaitlistChannel:
    def test_sms_when_opted_in(self, test_user: Profile, test_college: College):
        test_college.sms_enabled = True
        assert choose_waitlist_channel(test_user, test_college) == "sms"

    def test_email_when_phone_on_file_but_sms_not_opted_in(
        self, test_user: Profile, test_college: College
    ):
        assert test_user.phone
        test_college.sms_enabled = False
        assert choose_waitlist_channel(test_user, test_college) == "email"

    def test_email_when_user_has_no_phone(
        self, test_user: Profile, test_college: College
    ):
        test_user.phone = None
        test_college.sms_enabled = True
        assert choose_waitlist_channel(test_user, test_college) == "email"

    def test_email_for_guests(self, test_college: College):
        test_college.sms_enabled = True
        assert choose_waitlist_channel(None, test_college) == "email"


class TestNotifyRecoveredWaitlists:
    @pytest.mark.unit
    def test_notifies_pending_rows_when_data_is_ok(
        self, test_db: Session, test_college: College, test_user: Profile
    ):
        test_college.sms_enabled = True
        guest_row = _waitlist_row(test_college.id, email="guest@example.com")
        user_row = _waitlist_row(
            test_college.id, user_id=test_user.id, email=test_user.email
        )
        test_db.add_all([guest_row, user_row])
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()
        sms_service.is_enabled = True
        sms_service.send_data_restored_notification.return_value = True

        result = notify_recovered_college_waitlists(
            test_db,
            email_service=email_service,
            sms_service=sms_service,
        )

        assert result["sent"] == 2
        assert result["failed"] == 0
        test_db.refresh(guest_row)
        test_db.refresh(user_row)
        assert guest_row.notified_at is not None
        assert user_row.notified_at is not None
        email_service.send_data_restored_notification.assert_called_once_with(
            "guest@example.com", test_college.name, test_college.id
        )
        sms_service.send_data_restored_notification.assert_called_once_with(
            test_user.phone, test_college.name, test_college.id
        )

    @pytest.mark.unit
    def test_notify_is_idempotent(self, test_db: Session, test_college: College):
        row = _waitlist_row(test_college.id, email="guest@example.com")
        test_db.add(row)
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()

        first = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )
        second = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )

        assert first["sent"] == 1
        assert second["sent"] == 0
        assert second["examined"] == 0
        assert email_service.send_data_restored_notification.call_count == 1
        test_db.refresh(row)
        assert test_db.query(CollegeDataWaitlist).count() == 1

    @pytest.mark.unit
    def test_does_not_notify_while_stale(self, test_db: Session, test_college: College):
        test_college.data_available = False
        test_db.add(_waitlist_row(test_college.id, email="guest@example.com"))
        test_db.commit()

        email_service = MagicMock()
        result = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=MagicMock()
        )

        assert result["sent"] == 0
        email_service.send_data_restored_notification.assert_not_called()
        remaining = test_db.query(CollegeDataWaitlist).one()
        assert remaining.notified_at is None

    @pytest.mark.unit
    def test_does_not_notify_inactive_college(
        self, test_db: Session, test_college: College
    ):
        test_college.is_active = False
        test_db.add(_waitlist_row(test_college.id, email="guest@example.com"))
        test_db.commit()

        email_service = MagicMock()
        result = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=MagicMock()
        )

        assert result["sent"] == 0
        email_service.send_data_restored_notification.assert_not_called()

    @pytest.mark.unit
    def test_email_when_phone_on_file_but_sms_not_opted_in(
        self, test_db: Session, test_college: College, test_user: Profile
    ):
        """Phone on file is not enough; college.sms_enabled is the SMS opt-in."""
        assert test_user.phone
        test_college.sms_enabled = False
        test_db.add(
            _waitlist_row(test_college.id, user_id=test_user.id, email=test_user.email)
        )
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()
        sms_service.is_enabled = True

        result = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )

        assert result["sent"] == 1
        email_service.send_data_restored_notification.assert_called_once_with(
            test_user.email, test_college.name, test_college.id
        )
        sms_service.send_data_restored_notification.assert_not_called()

    def test_sms_when_opted_in(
        self, test_db: Session, test_college: College, test_user: Profile
    ):
        test_college.sms_enabled = True
        test_db.add(
            _waitlist_row(test_college.id, user_id=test_user.id, email=test_user.email)
        )
        test_db.commit()

        email_service = MagicMock()
        sms_service = MagicMock()
        sms_service.is_enabled = True
        sms_service.send_data_restored_notification.return_value = True

        result = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )

        assert result["sent"] == 1
        sms_service.send_data_restored_notification.assert_called_once_with(
            test_user.phone, test_college.name, test_college.id
        )
        email_service.send_data_restored_notification.assert_not_called()

    def test_email_when_signed_in_user_has_no_phone(
        self, test_db: Session, test_college: College, test_user: Profile
    ):
        test_user.phone = None
        test_college.sms_enabled = True
        test_db.add(
            _waitlist_row(test_college.id, user_id=test_user.id, email=test_user.email)
        )
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()
        sms_service.is_enabled = True

        result = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )

        assert result["sent"] == 1
        email_service.send_data_restored_notification.assert_called_once()
        sms_service.send_data_restored_notification.assert_not_called()

    @pytest.mark.unit
    def test_failed_send_is_retried(self, test_db: Session, test_college: College):
        row = _waitlist_row(test_college.id, email="guest@example.com")
        test_db.add(row)
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.side_effect = [False, True]
        sms_service = MagicMock()

        first = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )
        test_db.refresh(row)
        assert first["failed"] == 1
        assert row.notified_at is None
        assert row.attempts == 1
        assert row.last_attempt_at is not None

        second = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )
        test_db.refresh(row)
        assert second["sent"] == 1
        assert row.notified_at is not None

    @pytest.mark.unit
    def test_exhausted_rows_do_not_starve_fresh_batch(
        self, test_db: Session, test_college: College
    ):
        """Oldest-first LIMIT must skip exhausted rows in SQL."""
        batch_limit = 2
        older = datetime.now(timezone.utc) - timedelta(days=1)
        test_db.add_all(
            [
                _waitlist_row(
                    test_college.id,
                    email=f"exhausted{i}@example.com",
                    attempts=MAX_WAITLIST_ATTEMPTS,
                    created_at=older,
                )
                for i in range(batch_limit + 1)
            ]
        )
        fresh = _waitlist_row(test_college.id, email="fresh@example.com")
        test_db.add(fresh)
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True

        result = notify_recovered_college_waitlists(
            test_db,
            batch_limit=batch_limit,
            email_service=email_service,
            sms_service=MagicMock(),
        )

        assert result["sent"] == 1
        assert result["examined"] == 1
        test_db.refresh(fresh)
        assert fresh.notified_at is not None
        email_service.send_data_restored_notification.assert_called_once_with(
            "fresh@example.com", test_college.name, test_college.id
        )
        exhausted = (
            test_db.query(CollegeDataWaitlist)
            .filter(CollegeDataWaitlist.attempts >= MAX_WAITLIST_ATTEMPTS)
            .all()
        )
        assert len(exhausted) == batch_limit + 1
        assert all(row.notified_at is None for row in exhausted)

    @pytest.mark.unit
    def test_batch_limit(self, test_db: Session, test_college: College):
        test_db.add_all(
            [
                _waitlist_row(test_college.id, email="a@example.com"),
                _waitlist_row(test_college.id, email="b@example.com"),
                _waitlist_row(test_college.id, email="c@example.com"),
            ]
        )
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True

        result = notify_recovered_college_waitlists(
            test_db,
            batch_limit=2,
            email_service=email_service,
            sms_service=MagicMock(),
        )
        assert result["examined"] == 2
        assert result["sent"] == 2
        pending = (
            test_db.query(CollegeDataWaitlist)
            .filter(CollegeDataWaitlist.notified_at.is_(None))
            .count()
        )
        assert pending == 1

    @pytest.mark.unit
    def test_register_does_not_delete(self, test_db: Session, test_college: College):
        first = register_waitlist(test_db, test_college.id, email="guest@example.com")
        notified_at = datetime.now(timezone.utc)
        first.notified_at = notified_at
        test_db.commit()

        second = register_waitlist(test_db, test_college.id, email="guest@example.com")
        assert second.id == first.id
        assert second.notified_at is not None
        assert test_db.query(CollegeDataWaitlist).count() == 1

    @pytest.mark.unit
    def test_no_deliverable_address_counts_as_attempt(
        self, test_db: Session, test_college: College, test_user: Profile
    ):
        test_user.email = ""
        test_user.phone = None
        test_db.add(_waitlist_row(test_college.id, user_id=test_user.id, email=None))
        test_db.commit()

        email_service = MagicMock()
        sms_service = MagicMock()

        first = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )
        row = test_db.query(CollegeDataWaitlist).one()
        assert first["failed"] == 1
        assert first["sent"] == 0
        assert row.attempts == 1
        assert row.last_attempt_at is not None
        assert row.notified_at is None
        email_service.send_data_restored_notification.assert_not_called()
        sms_service.send_data_restored_notification.assert_not_called()

        for expected in range(2, MAX_WAITLIST_ATTEMPTS + 1):
            result = notify_recovered_college_waitlists(
                test_db, email_service=email_service, sms_service=sms_service
            )
            test_db.refresh(row)
            assert result["failed"] == 1
            assert row.attempts == expected

        aged_out = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )
        test_db.refresh(row)
        assert aged_out["examined"] == 0
        assert row.attempts == MAX_WAITLIST_ATTEMPTS
        assert row.notified_at is None

    @pytest.mark.unit
    def test_stops_after_max_attempts(self, test_db: Session, test_college: College):
        row = _waitlist_row(test_college.id, email="guest@example.com")
        test_db.add(row)
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = False
        sms_service = MagicMock()

        for expected in range(1, MAX_WAITLIST_ATTEMPTS + 1):
            result = notify_recovered_college_waitlists(
                test_db, email_service=email_service, sms_service=sms_service
            )
            test_db.refresh(row)
            assert result["failed"] == 1
            assert result["sent"] == 0
            assert row.attempts == expected
            assert row.notified_at is None
            assert row.last_attempt_at is not None

        exhausted = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )
        test_db.refresh(row)
        assert exhausted["examined"] == 0
        assert exhausted["sent"] == 0
        assert exhausted["failed"] == 0
        assert row.attempts == MAX_WAITLIST_ATTEMPTS
        assert row.notified_at is None
        assert test_db.query(CollegeDataWaitlist).count() == 1
        assert (
            email_service.send_data_restored_notification.call_count
            == MAX_WAITLIST_ATTEMPTS
        )

    @pytest.mark.unit
    def test_send_timeout_counts_as_failure(
        self, test_db: Session, test_college: College
    ):
        row = _waitlist_row(test_college.id, email="guest@example.com")
        test_db.add(row)
        test_db.commit()

        async def hang(_to_email, _college_name):
            await asyncio.sleep(5)
            return True

        email_service = MagicMock()
        email_service.send_data_restored_notification = hang
        sms_service = MagicMock()

        with patch("utils.college_data_waitlist.WAITLIST_SEND_TIMEOUT_SECONDS", 0.01):
            result = notify_recovered_college_waitlists(
                test_db, email_service=email_service, sms_service=sms_service
            )

        test_db.refresh(row)
        assert result["failed"] == 1
        assert result["sent"] == 0
        assert row.attempts == 1
        assert row.notified_at is None
        assert row.last_attempt_at is not None


class TestNotifyFromNotificationJob:
    @pytest.mark.unit
    def test_execute_runs_waitlist_recovery(
        self, test_db: Session, test_college: College
    ):
        from notifications.send_notifs import NotificationJob

        test_db.add(_waitlist_row(test_college.id, email="guest@example.com"))
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()

        job = NotificationJob(dry_run=False)
        job.email_service = email_service
        job.sms_service = sms_service

        from unittest.mock import patch

        with patch("notifications.send_notifs.SessionLocal") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            result = job.execute()

        assert result["success"] is True
        email_service.send_data_restored_notification.assert_called_once()
        row = test_db.query(CollegeDataWaitlist).one()
        assert row.notified_at is not None
        assert test_db.query(CollegeDataWaitlist).count() == 1

    @pytest.mark.unit
    @freeze_time("2024-01-15 10:00:00")
    def test_waitlist_operational_error_does_not_block_seat_alerts(
        self,
        test_db: Session,
        test_college: College,
        test_user: Profile,
        test_class,
    ):
        """A waitlist DBAPI error must rollback so seat alerts still send."""
        from notifications.send_notifs import NotificationJob

        test_db.add(_waitlist_row(test_college.id, email="guest@example.com"))
        test_db.add(
            Subscription(
                user_id=test_user.id,
                class_id=test_class.class_id,
                college_id=test_college.id,
                is_active=True,
            )
        )
        test_db.add(
            Enrollment(
                class_id=test_class.class_id,
                college_id=test_college.id,
                enrollment_status="open",
                scraped_at=datetime.now(timezone.utc),
            )
        )
        test_db.commit()

        def explode_waitlist(db, **kwargs):
            try:
                db.execute(text("SELECT 1 FROM __missing_waitlist_recovery"))
            except DBAPIError as exc:
                raise OperationalError(
                    exc.statement,
                    exc.params,
                    exc.orig,
                ) from exc

        email_service = MagicMock()
        email_service.send_course_notification = AsyncMock(return_value=True)
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()
        sms_service.is_enabled = False

        job = NotificationJob(dry_run=False)
        job.email_service = email_service
        job.sms_service = sms_service

        with patch("notifications.send_notifs.SessionLocal") as mock_session, patch(
            "utils.college_data_waitlist.notify_recovered_college_waitlists",
            side_effect=explode_waitlist,
        ), patch.object(test_db, "rollback", wraps=test_db.rollback) as mock_rollback:
            mock_session.return_value.__enter__.return_value = test_db
            result = job.execute()

        assert result["success"] is True
        assert result["notifications_sent"] == 1
        email_service.send_course_notification.assert_called_once()
        assert mock_rollback.called
        remaining = test_db.query(CollegeDataWaitlist).one()
        assert remaining.notified_at is None
