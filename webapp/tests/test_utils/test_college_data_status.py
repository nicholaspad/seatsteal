"""Tests for college seat-data status derivation."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from models.college import College
from models.scraper import Scraper
from models.scraper_log import ScraperLog
from utils.college_data_status import (
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
            latest_outcome="success",
            latest_courses_created=12,
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.last_updated_at == NOW - timedelta(hours=2)

    @pytest.mark.unit
    def test_stale_when_no_success_in_24h(self):
        last_success = NOW - timedelta(hours=25)
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=last_success,
            latest_outcome="success",
            latest_courses_created=10,
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_stale_when_never_succeeded(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=None,
            latest_outcome="error",
            latest_courses_created=0,
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.last_updated_at is None

    @pytest.mark.unit
    def test_stale_when_latest_error_with_zero_courses(self):
        last_success = NOW - timedelta(hours=1)
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=last_success,
            latest_outcome="error",
            latest_courses_created=0,
            now=NOW,
        )
        assert status.data_status == "stale"
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_stale_when_latest_partial_with_zero_courses(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=1),
            latest_outcome="partial",
            latest_courses_created=0,
            now=NOW,
        )
        assert status.data_status == "stale"

    @pytest.mark.unit
    def test_ok_when_latest_partial_created_courses(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=1),
            latest_outcome="partial",
            latest_courses_created=3,
            now=NOW,
        )
        assert status.data_status == "ok"

    @pytest.mark.unit
    def test_admin_flag_forces_stale(self):
        status = derive_college_data_status(
            data_available=False,
            has_scraper=True,
            last_success_at=NOW - timedelta(minutes=10),
            latest_outcome="success",
            latest_courses_created=20,
            now=NOW,
        )
        assert status.data_status == "stale"

    @pytest.mark.unit
    def test_no_scraper_is_ok(self):
        status = derive_college_data_status(
            has_scraper=False,
            last_success_at=None,
            now=NOW,
        )
        assert status.data_status == "ok"
        assert status.last_updated_at is None

    @pytest.mark.unit
    def test_custom_stale_window(self):
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=NOW - timedelta(hours=5),
            latest_outcome="success",
            latest_courses_created=4,
            now=NOW,
            stale_after_hours=4,
        )
        assert status.data_status == "stale"

    @pytest.mark.unit
    def test_naive_datetime_treated_as_utc(self):
        naive = datetime(2026, 10, 18, 11, 0)
        status = derive_college_data_status(
            has_scraper=True,
            last_success_at=naive,
            latest_outcome="success",
            latest_courses_created=1,
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
) -> ScraperLog:
    log = ScraperLog(
        scraper_id=scraper.id,
        outcome=outcome,
        courses_created=courses_created,
        classes_created=0,
        enrollments_saved=0,
        started_at=started_at,
        completed_at=completed_at or started_at,
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
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_old_success_stale(self, test_db: Session, test_college: College):
        last_success = NOW - timedelta(hours=30)
        _add_scraper(test_db, test_college, last_success_at=last_success)

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "stale"
        assert status.last_updated_at == last_success

    @pytest.mark.unit
    def test_latest_error_zero_courses_stale(
        self, test_db: Session, test_college: College
    ):
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
        assert status.data_status == "stale"

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

    @pytest.mark.unit
    def test_admin_flag_overrides_healthy_scraper(
        self, test_db: Session, test_college: College
    ):
        _add_scraper(test_db, test_college, last_success_at=NOW - timedelta(minutes=5))
        test_college.data_available = False
        test_db.commit()

        status = get_college_data_status(test_db, test_college, now=NOW)
        assert status.data_status == "stale"

    @pytest.mark.unit
    def test_batch_status_map(self, test_db: Session, test_college: College):
        other = College(name="Other University", short_name="OU", is_active=True)
        test_db.add(other)
        test_db.commit()
        test_db.refresh(other)

        _add_scraper(test_db, test_college, last_success_at=NOW - timedelta(hours=40))

        status_map = get_colleges_data_status(test_db, [test_college, other], now=NOW)
        assert status_map[test_college.id].data_status == "stale"
        assert status_map[other.id].data_status == "ok"
