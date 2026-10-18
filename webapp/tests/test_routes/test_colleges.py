"""Tests for college API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from datetime import datetime, timedelta, timezone

from models.college import College
from models.scraper import Scraper
from models.scraper_log import ScraperLog
from models.user import Profile


class TestGetColleges:
    """Tests for GET /api/colleges/ endpoint."""

    @pytest.mark.unit
    async def test_get_colleges_success(
        self,
        client: AsyncClient,
        test_college: College,
    ):
        """Test successfully getting all active colleges."""
        response = await client.get("/api/colleges/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) >= 1
        assert any(c["id"] == test_college.id for c in data)
        assert any(c["name"] == test_college.name for c in data)

    @pytest.mark.unit
    async def test_get_colleges_only_active(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        """Test that only active colleges are returned."""
        # Create an inactive college
        inactive_college = College(
            name="Inactive University",
            short_name="IU",
            is_active=False,
        )
        test_db.add(inactive_college)
        test_db.commit()

        response = await client.get("/api/colleges/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert all(c["isActive"] is True for c in data)
        assert not any(c["name"] == "Inactive University" for c in data)

    @pytest.mark.unit
    async def test_get_colleges_empty(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test getting colleges when none exist."""
        # Note: test_college fixture not used, so no colleges in db
        response = await client.get("/api/colleges/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) == 0

    @pytest.mark.unit
    async def test_get_colleges_sorted_by_name(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test that colleges are sorted by name."""
        # Create multiple colleges
        colleges = [
            College(name="Zebra University", short_name="ZU", is_active=True),
            College(name="Alpha University", short_name="AU", is_active=True),
            College(name="Beta University", short_name="BU", is_active=True),
        ]
        for college in colleges:
            test_db.add(college)
        test_db.commit()

        response = await client.get("/api/colleges/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        names = [c["name"] for c in data]
        assert names == sorted(names)


class TestGetCollege:
    """Tests for GET /api/colleges/{college_id} endpoint."""

    @pytest.mark.unit
    async def test_get_college_success(
        self,
        client: AsyncClient,
        test_college: College,
    ):
        """Test successfully getting a specific college."""
        response = await client.get(f"/api/colleges/{test_college.id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["id"] == test_college.id
        assert data["name"] == test_college.name
        assert data["shortName"] == test_college.short_name
        assert data["isActive"] is True
        assert data["dataStatus"] == "ok"
        assert data["lastUpdatedAt"] is None

    @pytest.mark.unit
    async def test_get_college_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent college."""
        response = await client.get("/api/colleges/99999")

        assert response.status_code == 404
        assert "College not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_get_college_inactive(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test getting inactive college (should still return it)."""
        inactive_college = College(
            name="Inactive University",
            short_name="IU",
            is_active=False,
        )
        test_db.add(inactive_college)
        test_db.commit()
        test_db.refresh(inactive_college)

        response = await client.get(f"/api/colleges/{inactive_college.id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["isActive"] is False
        assert data["dataStatus"] == "ok"


class TestCollegeDataStatusApi:
    """Tests for dataStatus / lastUpdatedAt on college endpoints."""

    @pytest.mark.unit
    async def test_list_includes_stale_status_from_old_scrape(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        last_success = datetime.now(timezone.utc) - timedelta(hours=30)
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
            last_success_at=last_success,
        )
        test_db.add(scraper)
        test_db.commit()

        response = await client.get("/api/colleges/")
        assert response.status_code == 200
        college = next(c for c in response.json()["data"] if c["id"] == test_college.id)
        assert college["dataStatus"] == "stale"
        assert college["checkoutBlocked"] is True
        assert college["lastUpdatedAt"] is not None

    @pytest.mark.unit
    async def test_detail_banner_stale_but_checkout_allowed_after_two_errors(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        last_success = datetime.now(timezone.utc) - timedelta(hours=2)
        scraper = Scraper(
            college_id=test_college.id,
            status="error",
            last_success_at=last_success,
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)

        test_db.add_all(
            [
                ScraperLog(
                    scraper_id=scraper.id,
                    outcome="error",
                    courses_created=0,
                    started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
                    completed_at=datetime.now(timezone.utc) - timedelta(minutes=19),
                ),
                ScraperLog(
                    scraper_id=scraper.id,
                    outcome="error",
                    courses_created=0,
                    started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                    completed_at=datetime.now(timezone.utc),
                ),
            ]
        )
        test_db.commit()

        response = await client.get(f"/api/colleges/{test_college.id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["dataStatus"] == "stale"
        assert data["checkoutBlocked"] is False
        assert data["lastUpdatedAt"] is not None

    @pytest.mark.unit
    async def test_admin_flag_forces_stale_on_list(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        test_college.data_available = False
        test_db.commit()

        response = await client.get("/api/colleges/")
        college = next(c for c in response.json()["data"] if c["id"] == test_college.id)
        assert college["dataStatus"] == "stale"
        assert college["checkoutBlocked"] is True

    @pytest.mark.unit
    async def test_inactive_college_detail_stays_ok_with_stale_logs(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        inactive_college = College(
            name="Brown University",
            short_name="brown",
            is_active=False,
        )
        test_db.add(inactive_college)
        test_db.commit()
        test_db.refresh(inactive_college)
        test_db.add(
            Scraper(
                college_id=inactive_college.id,
                status="error",
                last_success_at=datetime.now(timezone.utc) - timedelta(days=300),
            )
        )
        test_db.commit()

        response = await client.get(f"/api/colleges/{inactive_college.id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["isActive"] is False
        assert data["dataStatus"] == "ok"
        assert data["checkoutBlocked"] is False


class TestCollegeDataWaitlist:
    """Tests for POST /api/colleges/{id}/data-waitlist."""

    @pytest.fixture(autouse=True)
    def _reset_rate_limit(self):
        from utils.college_data_waitlist import reset_waitlist_rate_limiter

        reset_waitlist_rate_limiter()
        yield
        reset_waitlist_rate_limiter()

    @pytest.mark.unit
    async def test_signed_in_signup(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college: College,
    ):
        response = await authenticated_client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        from models.college_data_waitlist import CollegeDataWaitlist

        rows = test_db.query(CollegeDataWaitlist).all()
        assert len(rows) == 1
        assert rows[0].user_id == test_user.id
        assert rows[0].email == test_user.email
        assert rows[0].notified_at is None

    @pytest.mark.unit
    async def test_signed_out_signup(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        response = await client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={"email": "visitor@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        from models.college_data_waitlist import CollegeDataWaitlist

        rows = test_db.query(CollegeDataWaitlist).all()
        assert len(rows) == 1
        assert rows[0].user_id is None
        assert rows[0].email == "visitor@example.com"

    @pytest.mark.unit
    async def test_signed_in_dedupe(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        first = await authenticated_client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={},
        )
        second = await authenticated_client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={},
        )
        assert first.status_code == 200
        assert second.status_code == 200

        from models.college_data_waitlist import CollegeDataWaitlist

        assert test_db.query(CollegeDataWaitlist).count() == 1

    @pytest.mark.unit
    async def test_email_dedupe_is_case_insensitive(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        first = await client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={"email": "Visitor@Example.com"},
        )
        second = await client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={"email": "visitor@example.com"},
        )
        assert first.status_code == 200
        assert second.status_code == 200

        from models.college_data_waitlist import CollegeDataWaitlist

        assert test_db.query(CollegeDataWaitlist).count() == 1

    @pytest.mark.unit
    async def test_invalid_email(
        self,
        client: AsyncClient,
        test_college: College,
    ):
        response = await client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422

    @pytest.mark.unit
    async def test_signed_out_requires_email(
        self,
        client: AsyncClient,
        test_college: College,
    ):
        response = await client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={},
        )
        assert response.status_code == 422

    @pytest.mark.unit
    async def test_unknown_college(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/colleges/99999/data-waitlist",
            json={"email": "visitor@example.com"},
        )
        assert response.status_code == 404

    @pytest.mark.unit
    async def test_rate_limited(
        self,
        client: AsyncClient,
        test_college: College,
    ):
        from utils.college_data_waitlist import WAITLIST_RATE_LIMIT

        for i in range(WAITLIST_RATE_LIMIT):
            response = await client.post(
                f"/api/colleges/{test_college.id}/data-waitlist",
                json={"email": f"visitor{i}@example.com"},
            )
            assert response.status_code == 200

        response = await client.post(
            f"/api/colleges/{test_college.id}/data-waitlist",
            json={"email": "toomany@example.com"},
        )
        assert response.status_code == 429
