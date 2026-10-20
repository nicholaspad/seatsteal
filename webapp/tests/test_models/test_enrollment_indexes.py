"""Enrollment index set after the 021 shrink."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.enrollment import Enrollment  # noqa: F401


KEPT_INDEXES = {
    "enrollments_pkey",
    "enrollments_class_scraped_idx",
    "enrollments_scraped_at_idx",
    "enrollments_college_scraped_idx",
}


class TestEnrollmentIndexes:
    @pytest.mark.unit
    def test_fresh_db_declares_only_kept_indexes(self, test_db: Session):
        names = set(
            test_db.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'public' AND tablename = 'enrollments'"
                )
            ).scalars()
        )
        assert names == KEPT_INDEXES
        assert "ix_enrollments_college_id" not in names
        assert "ix_enrollments_class_id" not in names
        assert "ix_enrollments_id" not in names
        assert "enrollments_class_id_idx" not in names
