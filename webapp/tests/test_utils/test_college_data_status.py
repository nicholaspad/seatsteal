"""Tests for college seat-data status derivation."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from models.college import College
from models.scraper import Scraper
from models.scraper_log import ScraperLog
from utils.college_data_status import (
    ORPHANED_BY_RESTART_MESSAGE,
    derive_college_data_status,
    get_college_data_status,
    get_colleges_data_status,
)


NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


class TestDeriveCollegeDataStatus:
    """Pure derivation cases — no database required."""

    @pytest.mark.unit
    def test_ok_when_recent_success(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=2),
            recent_runs=[("success", 12)],
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.checkout_blocked is False
        assert status.last_updated_at == NOW - timedelta(hours=2)

    @pytest.mark.unit
    def test_stale_and_checkout_blocked_when_no_success_in_24h(self):
        last_success = NOW - timedelta(hours=25)
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=last_success,
            recent_runs=[("success", 10)],
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.checkout_blocked is True
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_stale_when_never_succeeded(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=None,
            recent_runs=[("error", 0)],
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.checkout_blocked is True
        assert status.last_updated_at is None

    @pytest.mark.unit
    def test_single_error_stays_ok_when_recent_success(self):
        last_success = NOW - timedelta(hours=1)
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=last_success,
            recent_runs=[("error", 0)],
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.checkout_blocked is False
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_single_zero_course_partial_stays_ok(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=1),
            recent_runs=[("partial", 0)],
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_two_consecutive_errors_stale_but_checkout_allowed(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=2),
            recent_runs=[("error", 0), ("error", 0)],
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_error_then_success_then_error_stays_ok(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=1),
            recent_runs=[("error", 0), ("success", 8), ("error", 0)],
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_error_and_zero_course_partial_stale(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=1),
            recent_runs=[("partial", 0), ("error", 0)],
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_ok_when_latest_partial_created_courses(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=1),
            recent_runs=[("partial", 3), ("error", 0)],
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_admin_flag_forces_stale_and_blocks_checkout(self):
        status = derive_college_data_status(
            data_available=False,
            has_scraper=True,
            last_success_at=NOW - timedelta(minutes=10),
            recent_runs=[("success", 20)],
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.checkout_blocked is True

    @pytest.mark.unit
    def test_no_scraper_is_ok(self):
        status = derive_college_data_status(
            has_scraper=False,
            last_success_at=None,
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.checkout_blocked is False
        assert status.last_updated_at is None

    @pytest.mark.unit
    def test_inactive_college_stays_ok_despite_stale_logs(self):
        last_success = NOW - timedelta(days=300)
        status = derive_college_data_status(
            is_active=False,
            data_available=False,
            has_scraper=True,
            last_success_at=last_success,
            recent_runs=[("error", 0), ("error", 0)],
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.checkout_blocked is False
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_custom_stale_window(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=5),
            recent_runs=[("success", 4)],
            now=NOW,
            stale_after_hours=4,
        )
        assert status.data_status == "stale"
        assert status.checkout_blocked is True

    @pytest.mark.unit
    def test_naive_datetime_treated_as_utc(self):
        naive = datetime(2026, 10, 18, 11, 0)
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=naive,
            recent_runs=[("success", 1)],
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.last_updated_at.tzinfo == timezone.utc


def _add_scraper(db: Session, college: College, last_success_at=None) -> Scraper:
    scraper = Scraper(
        college_id=college.id,
        status="idle",
        last_success_at=last_success_at,
    )
    db.add(scraper)
    db.commit()
    db.refresh(scraper)
    return scraper


def _add_log(
    db: Session,
    scraper: Scraper,
    *,
    outcome: str,
    courses_created: int,
    started_at: datetime,
    completed_at: datetime | None = None,
    error_message: str | None = None,
) -> ScraperLog:
    log = ScraperLog(
        scraper_id=scraper.id,
        outcome=outcome,
        courses_created=courses_created,
        classes_created=0,
        enrollments_saved=0,
        started_at=started_at,
        completed_at=completed_at if completed_at is not None else started_at,
        error_message=error_message,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


class TestGetCollegeDataStatusFromDb:
    """Integration tests against the test database."""

    @pytest.mark.unit
    def test_no_scraper_ok(self, test_db: Session, test_college: College):
        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_recent_success_ok(self, test_db: Session, test_college: College):
        last_success = NOW - timedelta(hours=3)
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        _add_log(
            test_db,
            scraper,
            outcome="success",
            courses_created=8,
            started_at=last_success,
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_old_success_stale(self, test_db: Session, test_college: College):
        last_success = NOW - timedelta(hours=30)
        _add_scraper(test_db, test_college, last_success_at=last_success)

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "stale"
        assert status.checkout_blocked is True
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_single_error_stays_ok(self, test_db: Session, test_college: College):
        last_success = NOW - timedelta(hours=2)
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        _add_log(
            test_db,
            scraper,
            outcome="success",
            courses_created=5,
            started_at=last_success,
        )
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(minutes=10),
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_two_consecutive_errors_stale_checkout_allowed(
        self, test_db: Session, test_college: College
    ):
        last_success = NOW - timedelta(hours=3)
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        _add_log(
            test_db,
            scraper,
            outcome="success",
            courses_created=6,
            started_at=last_success,
        )
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(minutes=20),
        )
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(minutes=5),
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "stale"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_error_then_success_then_error_stays_ok(
        self, test_db: Session, test_college: College
    ):
        last_success = NOW - timedelta(hours=1)
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(hours=3),
        )
        _add_log(
            test_db,
            scraper,
            outcome="success",
            courses_created=9,
            started_at=last_success,
        )
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(minutes=8),
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_orphaned_by_restart_ignored_even_when_completed_at_newest(
        self, test_db: Session, test_college: College
    ):
        last_success = NOW - timedelta(hours=2)
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        _add_log(
            test_db,
            scraper,
            outcome="success",
            courses_created=7,
            started_at=last_success,
            completed_at=last_success,
        )
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(days=3),
            completed_at=NOW - timedelta(seconds=30),
            error_message=ORPHANED_BY_RESTART_MESSAGE,
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_orders_completed_runs_by_started_at(
        self, test_db: Session, test_college: College
    ):
        last_success = NOW - timedelta(hours=2)
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        # Older start, newest completed_at — must not be treated as latest.
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(hours=4),
            completed_at=NOW - timedelta(seconds=10),
        )
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(hours=3),
            completed_at=NOW - timedelta(minutes=2),
        )
        _add_log(
            test_db,
            scraper,
            outcome="success",
            courses_created=4,
            started_at=NOW - timedelta(minutes=10),
            completed_at=NOW - timedelta(hours=1),
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_running_log_ignored(self, test_db: Session, test_college: College):
        last_success = NOW - timedelta(hours=1)
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        _add_log(
            test_db,
            scraper,
            outcome="success",
            courses_created=4,
            started_at=last_success,
        )
        _add_log(
            test_db,
            scraper,
            outcome="running",
            courses_created=0,
            started_at=NOW - timedelta(minutes=2),
            completed_at=None,
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False

    @pytest.mark.unit
    def test_admin_flag_overrides_healthy_scraper(
        self, test_db: Session, test_college: College
    ):
        _add_scraper(test_db, test_college, last_success_at=NOW - timedelta(minutes=5))
        test_college.data_available = False
        test_db.commit()

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "stale"
        assert status.checkout_blocked is True

    @pytest.mark.unit
    def test_batch_status_map(self, test_db: Session, test_college: College):
        other = College(name="Other University", short_name="OU", is_active=True)
        test_db.add(other)
        test_db.commit()
        test_db.refresh(other)

        _add_scraper(test_db, test_college, last_success_at=NOW - timedelta(hours=40))

        status_map = get_colleges_data_status(test_db, [test_college, other], now=NOW)
        assert status_map[test_college.id].data_status == "stale"
        assert status_map[test_college.id].checkout_blocked is True
        assert status_map[other.id].data_status == "ok"
        assert status_map[other.id].checkout_blocked is False

    @pytest.mark.unit
    def test_inactive_college_with_stale_error_logs_is_ok(
        self, test_db: Session, test_college: College
    ):
        """Dropped schools (Brown/UF) must not show a banner or block checkout."""
        last_success = NOW - timedelta(days=300)
        test_college.is_active = False
        test_db.commit()
        scraper = _add_scraper(test_db, test_college, last_success_at=last_success)
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(days=2),
        )
        _add_log(
            test_db,
            scraper,
            outcome="error",
            courses_created=0,
            started_at=NOW - timedelta(hours=1),
        )

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "ok"
        assert status.checkout_blocked is False
        assert status.last_updated_at == last_success
