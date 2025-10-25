"""Tests for admin API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from datetime import datetime

from webapp.models.user import Profile
from webapp.models.subscription import Subscription
from webapp.models.notification_log import NotificationLog
from webapp.models.query_performance_metric import QueryPerformanceMetric
from webapp.models.scraper import Scraper
from webapp.models.scraper_log import ScraperLog


class TestGetAnalytics:
    """Tests for GET /api/admin/analytics endpoint."""

    @pytest.mark.unit
    async def test_get_analytics_success(
        self,
        admin_client: AsyncClient,
        test_admin_user: Profile,
        test_subscription: Subscription,
    ):
        """Test successfully getting analytics (admin only)."""
        response = await admin_client.get("/api/admin/analytics")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert "overview" in data
        assert "popularCourses" in data
        assert "collegeStats" in data

    @pytest.mark.unit
    async def test_get_analytics_with_timeframe(
        self,
        admin_client: AsyncClient,
        test_admin_user: Profile,
    ):
        """Test analytics with custom timeframe."""
        response = await admin_client.get("/api/admin/analytics?timeframe=7")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True

    @pytest.mark.unit
    async def test_get_analytics_with_college_filter(
        self,
        admin_client: AsyncClient,
        test_admin_user: Profile,
        test_college,
    ):
        """Test analytics filtered by college."""
        response = await admin_client.get(
            f"/api/admin/analytics?college={test_college.id}"
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True

    @pytest.mark.unit
    async def test_get_analytics_non_admin(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test that non-admin users cannot access analytics."""
        response = await authenticated_client.get("/api/admin/analytics")

        assert response.status_code == 403

    @pytest.mark.unit
    async def test_get_analytics_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test analytics without authentication."""
        response = await client.get("/api/admin/analytics")

        assert response.status_code == 401


class TestGetNotifications:
    """Tests for GET /api/admin/notifications endpoint."""

    @pytest.mark.unit
    async def test_get_notifications_success(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
    ):
        """Test successfully getting notification logs."""
        # Create notification log
        log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            notification_type="email",
            message="Test notification",
            status="sent",
            sent_at=datetime.utcnow(),
        )
        test_db.add(log)
        test_db.commit()

        response = await admin_client.get("/api/admin/notifications")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) >= 1

    @pytest.mark.unit
    async def test_get_notifications_non_admin(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that non-admin users cannot access notifications."""
        response = await authenticated_client.get("/api/admin/notifications")

        assert response.status_code == 403


class TestGetQueryPerformance:
    """Tests for GET /api/admin/query-performance endpoint."""

    @pytest.mark.unit
    async def test_get_query_performance_success(
        self,
        admin_client: AsyncClient,
        test_db: Session,
    ):
        """Test successfully getting query performance metrics."""
        # Create metric
        metric = QueryPerformanceMetric(
            query_name="test_query",
            execution_time=0.5,
            executed_at=datetime.utcnow(),
        )
        test_db.add(metric)
        test_db.commit()

        response = await admin_client.get("/api/admin/query-performance")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) >= 1

    @pytest.mark.unit
    async def test_get_query_performance_non_admin(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that non-admin users cannot access query performance."""
        response = await authenticated_client.get("/api/admin/query-performance")

        assert response.status_code == 403


class TestGetScrapers:
    """Tests for GET /api/admin/scrapers endpoint."""

    @pytest.mark.unit
    async def test_get_scrapers_success(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_college,
    ):
        """Test successfully getting scraper status."""
        # Create scraper
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)

        response = await admin_client.get("/api/admin/scrapers")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) >= 1

    @pytest.mark.unit
    async def test_get_scrapers_with_logs(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_college,
    ):
        """Test getting scrapers with latest logs."""
        # Create scraper
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)

        # Create log
        log = ScraperLog(
            scraper_id=scraper.id,
            outcome="success",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        test_db.add(log)
        test_db.commit()

        response = await admin_client.get("/api/admin/scrapers")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        scraper_data = next(s for s in data if s["id"] == scraper.id)
        assert scraper_data["latestLog"] is not None

    @pytest.mark.unit
    async def test_get_scrapers_non_admin(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that non-admin users cannot access scrapers."""
        response = await authenticated_client.get("/api/admin/scrapers")

        assert response.status_code == 403


class TestGetUsers:
    """Tests for GET /api/admin/users endpoint."""

    @pytest.mark.unit
    async def test_get_users_success(
        self,
        admin_client: AsyncClient,
        test_user: Profile,
    ):
        """Test successfully getting all users."""
        response = await admin_client.get("/api/admin/users")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) >= 1

    @pytest.mark.unit
    async def test_get_users_non_admin(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that non-admin users cannot access users list."""
        response = await authenticated_client.get("/api/admin/users")

        assert response.status_code == 403


class TestGetUser:
    """Tests for GET /api/admin/users/{user_id} endpoint."""

    @pytest.mark.unit
    async def test_get_user_success(
        self,
        admin_client: AsyncClient,
        test_user: Profile,
    ):
        """Test successfully getting a specific user."""
        response = await admin_client.get(f"/api/admin/users/{test_user.id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email

    @pytest.mark.unit
    async def test_get_user_not_found(
        self,
        admin_client: AsyncClient,
    ):
        """Test getting non-existent user."""
        from uuid import uuid4

        response = await admin_client.get(f"/api/admin/users/{uuid4()}")

        assert response.status_code == 404

    @pytest.mark.unit
    async def test_get_user_non_admin(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test that non-admin users cannot access specific user."""
        response = await authenticated_client.get(f"/api/admin/users/{test_user.id}")

        assert response.status_code == 403


class TestUpdateUser:
    """Tests for PATCH /api/admin/users/{user_id} endpoint."""

    @pytest.mark.unit
    async def test_update_user_role_success(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test successfully updating user role."""
        response = await admin_client.patch(
            f"/api/admin/users/{test_user.id}",
            json={"role": "admin"},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["role"] == "admin"

        # Verify in database
        test_db.refresh(test_user)
        assert test_user.role == "admin"

    @pytest.mark.unit
    async def test_update_user_college_success(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test successfully updating user college."""
        from webapp.models.college import College

        new_college = College(
            name="New Admin University",
            short_name="NAU",
            is_active=True,
        )
        test_db.add(new_college)
        test_db.commit()
        test_db.refresh(new_college)

        response = await admin_client.patch(
            f"/api/admin/users/{test_user.id}",
            json={"college_id": new_college.id},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["collegeId"] == new_college.id

    @pytest.mark.unit
    async def test_update_user_not_found(
        self,
        admin_client: AsyncClient,
    ):
        """Test updating non-existent user."""
        from uuid import uuid4

        response = await admin_client.patch(
            f"/api/admin/users/{uuid4()}",
            json={"role": "admin"},
        )

        assert response.status_code == 404

    @pytest.mark.unit
    async def test_update_user_non_admin(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test that non-admin users cannot update users."""
        response = await authenticated_client.patch(
            f"/api/admin/users/{test_user.id}",
            json={"role": "admin"},
        )

        assert response.status_code == 403
