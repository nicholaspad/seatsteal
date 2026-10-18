"""Tests for college data waitlist recovery notifications."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from models.college import College
from models.college_data_waitlist import CollegeDataWaitlist
from models.user import Profile
from utils.college_data_waitlist import (
    choose_waitlist_channel,
    notify_recovered_college_waitlists,
    register_waitlist,
)


def _waitlist_row(
    college_id: int,
    *,
    user_id=None,
    email=None,
    notified_at=None,
) -> CollegeDataWaitlist:
    return CollegeDataWaitlist(
        college_id=college_id,
        user_id=user_id,
        email=email,
        notified_at=notified_at,
    )


class TestChooseWaitlistChannel:
    def test_sms_when_user_has_phone(self, test_user: Profile):
        assert choose_waitlist_channel(test_user) == "sms"

    def test_email_when_user_has_no_phone(self, test_user: Profile):
        test_user.phone = None
        assert choose_waitlist_channel(test_user) == "email"

    def test_email_for_guests(self):
        assert choose_waitlist_channel(None) == "email"


class TestNotifyRecoveredWaitlists:
    @pytest.mark.unit
    def test_notifies_pending_rows_when_data_is_ok(
        self, test_db: Session, test_college: College, test_user: Profile
    ):
        guest_row = _waitlist_row(test_college.id, email="guest@example.com")
        user_row = _waitlist_row(
            test_college.id, user_id=test_user.id, email=test_user.email
        )
        test_db.add_all([guest_row, user_row])
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()
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
            "guest@example.com", test_college.name
        )
        sms_service.send_data_restored_notification.assert_called_once_with(
            test_user.phone, test_college.name
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
    def test_email_when_signed_in_user_has_no_phone(
        self, test_db: Session, test_college: College, test_user: Profile
    ):
        test_user.phone = None
        test_db.add(
            _waitlist_row(test_college.id, user_id=test_user.id, email=test_user.email)
        )
        test_db.commit()

        email_service = MagicMock()
        email_service.send_data_restored_notification.return_value = True
        sms_service = MagicMock()

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

        second = notify_recovered_college_waitlists(
            test_db, email_service=email_service, sms_service=sms_service
        )
        test_db.refresh(row)
        assert second["sent"] == 1
        assert row.notified_at is not None

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
