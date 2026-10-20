"""Tests for prune_enrollment_history.py."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from tests.conftest import TEST_DATABASE_URL

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from prune_enrollment_history import run_prune  # noqa: E402

from models.class_model import Class
from models.college import College
from models.course import Course
from models.enrollment import Enrollment
from models.notification_log import NotificationLog
from models.subscription import Subscription
from models.user import Profile


def _add_class(db: Session, course: Course, class_number: str) -> Class:
    cls = Class(
        course_id=course.id,
        class_number=class_number,
        section_code="A",
        is_active=True,
    )
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


def _add_enrollment(
    db: Session, cls: Class, college: College, days_ago: int, status: str = "closed"
) -> Enrollment:
    row = Enrollment(
        class_id=cls.class_id,
        college_id=college.id,
        enrollment_status=status,
        scraped_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _prune(
    test_db: Session, *, confirm: bool, keep_days: int = 30, batch_size: int = 2000
):
    test_db.commit()
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            return run_prune(
                conn,
                keep_days=keep_days,
                college_id=None,
                batch_size=batch_size,
                sleep_s=0,
                confirm=confirm,
            )
    finally:
        engine.dispose()
        test_db.expire_all()


def _enrollment_ids(test_db: Session, cls: Class) -> set[int]:
    return set(
        test_db.execute(
            text("SELECT id FROM enrollments WHERE class_id = :cid"),
            {"cid": cls.class_id},
        ).scalars()
    )


def _row_exists(test_db: Session, table: str, pk_col: str, pk: int) -> bool:
    return (
        test_db.execute(
            text(f"SELECT 1 FROM {table} WHERE {pk_col} = :pk"),
            {"pk": pk},
        ).scalar()
        is not None
    )


class TestPruneEnrollmentHistory:
    @pytest.mark.unit
    def test_dry_run_deletes_nothing(
        self, test_db: Session, test_college: College, test_course: Course
    ):
        cls = _add_class(test_db, test_course, "1001")
        kept = _add_enrollment(test_db, cls, test_college, 1, status="open")
        _add_enrollment(test_db, cls, test_college, 35)
        _add_enrollment(test_db, cls, test_college, 40)
        before = test_db.query(Enrollment).count()

        total, deleted = _prune(test_db, confirm=False)

        assert total == 2
        assert deleted == 0
        assert test_db.query(Enrollment).count() == before == 3
        assert kept.id in _enrollment_ids(test_db, cls)
        assert len(_enrollment_ids(test_db, cls)) == 3

    @pytest.mark.unit
    def test_confirm_keeps_latest_per_class_and_other_tables(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        test_user: Profile,
        test_class: Class,
        test_subscription: Subscription,
    ):
        # (2) three rows: 40d, 35d, 1d — delete the two old ones
        three_row = _add_class(test_db, test_course, "2001")
        recent = _add_enrollment(test_db, three_row, test_college, 1, status="open")
        old_35 = _add_enrollment(test_db, three_row, test_college, 35)
        old_40 = _add_enrollment(test_db, three_row, test_college, 40)
        recent_id, old_35_id, old_40_id = recent.id, old_35.id, old_40.id

        # (3) only row is 40d old — keep it
        only_old = _add_class(test_db, test_course, "2002")
        only_row = _add_enrollment(test_db, only_old, test_college, 40)
        only_row_id = only_row.id

        # (4) latest row is 40d old — keep that, drop older
        stale_latest = _add_class(test_db, test_course, "2003")
        latest_old = _add_enrollment(test_db, stale_latest, test_college, 40)
        older_45 = _add_enrollment(test_db, stale_latest, test_college, 45)
        older_50 = _add_enrollment(test_db, stale_latest, test_college, 50)
        latest_old_id, older_45_id, older_50_id = (
            latest_old.id,
            older_45.id,
            older_50.id,
        )

        log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_college.id,
            user_id=test_user.id,
            notification_type="email",
            message="seat open",
            status="sent",
            sent_at=datetime.now(timezone.utc),
        )
        test_db.add(log)
        test_db.commit()
        log_id = log.id
        subscription_id = test_subscription.id
        class_pk = test_class.class_id

        sub_count = test_db.query(Subscription).count()
        log_count = test_db.query(NotificationLog).count()
        class_count = test_db.query(Class).count()

        total, deleted = _prune(test_db, confirm=True, batch_size=2)

        assert total == 4
        assert deleted == 4
        assert _enrollment_ids(test_db, three_row) == {recent_id}
        assert not _row_exists(test_db, "enrollments", "id", old_35_id)
        assert not _row_exists(test_db, "enrollments", "id", old_40_id)
        assert _enrollment_ids(test_db, only_old) == {only_row_id}
        assert _enrollment_ids(test_db, stale_latest) == {latest_old_id}
        assert not _row_exists(test_db, "enrollments", "id", older_45_id)
        assert not _row_exists(test_db, "enrollments", "id", older_50_id)

        assert test_db.query(Subscription).count() == sub_count
        assert test_db.query(NotificationLog).count() == log_count
        assert test_db.query(Class).count() == class_count
        assert _row_exists(test_db, "subscriptions", "id", subscription_id)
        assert _row_exists(test_db, "notification_logs", "id", log_id)
        assert _row_exists(test_db, "classes", "class_id", class_pk)

    @pytest.mark.unit
    def test_main_is_dry_run_without_confirm(
        self,
        test_db: Session,
        test_college: College,
        test_course: Course,
        monkeypatch,
        capsys,
    ):
        cls = _add_class(test_db, test_course, "3001")
        _add_enrollment(test_db, cls, test_college, 1, status="open")
        _add_enrollment(test_db, cls, test_college, 40)
        test_db.commit()

        import prune_enrollment_history as prune_mod

        monkeypatch.setattr(prune_mod.settings, "DATABASE_URL", TEST_DATABASE_URL)
        monkeypatch.setattr(
            sys, "argv", ["prune_enrollment_history.py", "--keep-days", "30"]
        )
        prune_mod.main()

        captured = capsys.readouterr().out
        assert "Dry run" in captured
        assert test_db.query(Enrollment).count() == 2
