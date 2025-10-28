"""Tests for admin API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.user import Profile
from models.subscription import Subscription
from models.notification_log import NotificationLog
from models.query_performance_metric import QueryPerformanceMetric
from models.scraper import Scraper
from models.scraper_log import ScraperLog
from models.course import Course
from models.college import College
from models.class_model import Class
from models.enrollment import Enrollment


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
        assert "notificationTrends" in data
        assert "recentEnrollmentChanges" in data

        # Verify overview structure
        overview = data["overview"]
        assert "totalUsers" in overview
        assert "adminUsers" in overview
        assert "totalSubscriptions" in overview
        assert "activeSubscriptions" in overview
        assert "totalNotifications" in overview
        assert "notificationSuccessRate" in overview
        assert overview["totalUsers"] >= 0
        assert overview["totalSubscriptions"] >= 0

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
        data = response_json["data"]
        assert "overview" in data

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
        data = response_json["data"]
        assert "overview" in data

    @pytest.mark.unit
    async def test_get_analytics_empty_data(
        self,
        admin_client: AsyncClient,
        test_admin_user: Profile,
    ):
        """Test analytics with no data returns proper structure."""
        response = await admin_client.get("/api/admin/analytics?timeframe=365")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert isinstance(data["popularCourses"], list)
        assert isinstance(data["collegeStats"], list)
        assert isinstance(data["notificationTrends"], list)

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
        assert "notifications" in data
        assert "colleges" in data
        assert "pagination" in data
        assert len(data["notifications"]) >= 1

        # Verify notification structure
        notif = data["notifications"][0]
        assert "id" in notif
        assert "sentAt" in notif
        assert "notificationType" in notif
        assert "status" in notif

    @pytest.mark.unit
    async def test_get_notifications_pagination(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
    ):
        """Test notifications pagination."""
        # Create multiple notification logs
        for i in range(15):
            log = NotificationLog(
                subscription_id=test_subscription.id,
                college_id=test_subscription.college_id,
                notification_type="email",
                message=f"Test notification {i}",
                status="sent",
                sent_at=datetime.utcnow(),
            )
            test_db.add(log)
        test_db.commit()

        # Test first page
        response = await admin_client.get("/api/admin/notifications?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["notifications"]) <= 10
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["totalCount"] >= 15

        # Test second page
        response = await admin_client.get("/api/admin/notifications?page=2&limit=10")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pagination"]["page"] == 2

    @pytest.mark.unit
    async def test_get_notifications_filter_by_status(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
    ):
        """Test filtering notifications by status."""
        # Create notifications with different statuses
        log1 = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            notification_type="email",
            message="Success",
            status="sent",
            sent_at=datetime.utcnow(),
        )
        log2 = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            notification_type="email",
            message="Failed",
            status="failed",
            sent_at=datetime.utcnow(),
        )
        test_db.add_all([log1, log2])
        test_db.commit()

        response = await admin_client.get("/api/admin/notifications?status=sent")
        assert response.status_code == 200
        data = response.json()["data"]
        for notif in data["notifications"]:
            assert notif["status"] == "sent"

    @pytest.mark.unit
    async def test_get_notifications_search(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
    ):
        """Test searching notifications."""
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

        # Search by email
        response = await admin_client.get(
            f"/api/admin/notifications?search={test_user.email[:5]}"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["notifications"]) >= 0

    @pytest.mark.unit
    async def test_get_notifications_invalid_page(
        self,
        admin_client: AsyncClient,
    ):
        """Test invalid page parameter."""
        response = await admin_client.get("/api/admin/notifications?page=0")
        assert response.status_code == 422  # Validation error

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
        # Create metrics
        metric1 = QueryPerformanceMetric(
            query_name="test_query",
            execution_time=50.0,
            executed_at=datetime.utcnow(),
            result_count=10,
        )
        metric2 = QueryPerformanceMetric(
            query_name="slow_query",
            execution_time=150.0,
            executed_at=datetime.utcnow(),
            result_count=100,
        )
        test_db.add_all([metric1, metric2])
        test_db.commit()

        response = await admin_client.get("/api/admin/query-performance")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert "stats" in data
        assert "recentSlowQueries" in data
        assert "hourlyPercentiles" in data

        # Verify stats structure
        stats = data["stats"]
        assert "totalQueries" in stats
        assert "slowQueries" in stats
        assert "avgExecutionTime" in stats
        assert "slowQueryPercentage" in stats
        assert stats["totalQueries"] >= 2
        assert stats["slowQueries"] >= 1  # slow_query is > 100ms

    @pytest.mark.unit
    async def test_get_query_performance_empty_metrics(
        self,
        admin_client: AsyncClient,
    ):
        """Test query performance with no metrics."""
        response = await admin_client.get("/api/admin/query-performance")

        assert response.status_code == 200
        data = response.json()["data"]
        stats = data["stats"]
        assert stats["totalQueries"] == 0
        assert stats["slowQueries"] == 0
        assert stats["avgExecutionTime"] == 0
        assert stats["slowQueryPercentage"] == 0

    @pytest.mark.unit
    async def test_get_query_performance_slow_query_threshold(
        self,
        admin_client: AsyncClient,
        test_db: Session,
    ):
        """Test that slow queries are properly identified."""
        # Create metrics with varying execution times
        for i, exec_time in enumerate([50.0, 99.0, 100.0, 101.0, 200.0]):
            metric = QueryPerformanceMetric(
                query_name=f"query_{i}",
                execution_time=exec_time,
                executed_at=datetime.utcnow(),
            )
            test_db.add(metric)
        test_db.commit()

        response = await admin_client.get("/api/admin/query-performance")
        data = response.json()["data"]
        stats = data["stats"]

        # Only queries > 100ms should be considered slow
        assert stats["totalQueries"] == 5
        assert stats["slowQueries"] == 2  # 101.0 and 200.0

    @pytest.mark.unit
    async def test_get_query_performance_hourly_percentiles(
        self,
        admin_client: AsyncClient,
        test_db: Session,
    ):
        """Test hourly percentile calculations."""
        # Create metrics from the last few hours
        now = datetime.utcnow()
        for hour in range(5):
            for i in range(10):
                metric = QueryPerformanceMetric(
                    query_name=f"query_{hour}_{i}",
                    execution_time=float(i * 10),
                    executed_at=now - timedelta(hours=hour, minutes=i),
                )
                test_db.add(metric)
        test_db.commit()

        response = await admin_client.get("/api/admin/query-performance")
        data = response.json()["data"]
        percentiles = data["hourlyPercentiles"]

        assert len(percentiles) > 0
        for item in percentiles:
            assert "hour" in item
            assert "p50" in item
            assert "p90" in item
            assert "queryCount" in item

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
        assert "overview" in data
        assert "scraperDetails" in data
        assert "successRateTrends" in data
        assert "performanceTrends" in data
        assert "recentActivity" in data
        assert "collegeStats" in data

        # Verify overview structure
        overview = data["overview"]
        assert "totalScrapers" in overview
        assert "activeScrapers" in overview
        assert "errorScrapers" in overview
        assert "successRate" in overview

    @pytest.mark.unit
    async def test_get_scrapers_with_logs(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_college,
    ):
        """Test getting scrapers with logs."""
        # Create scraper
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)

        # Create logs
        log1 = ScraperLog(
            scraper_id=scraper.id,
            outcome="success",
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=2),
            duration_ms=1000,
            courses_created=5,
            classes_created=20,
            enrollments_saved=100,
        )
        log2 = ScraperLog(
            scraper_id=scraper.id,
            outcome="error",
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow() - timedelta(hours=1),
            error_message="Test error",
        )
        test_db.add_all([log1, log2])
        test_db.commit()

        response = await admin_client.get("/api/admin/scrapers")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["recentActivity"]) >= 2
        assert len(data["recentErrorDetails"]) >= 1

    @pytest.mark.unit
    async def test_get_scrapers_with_college_filter(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_college,
    ):
        """Test filtering scrapers by college."""
        # Create scrapers for test college
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
        )
        test_db.add(scraper)
        test_db.commit()

        response = await admin_client.get(
            f"/api/admin/scrapers?college={test_college.id}"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        overview = data["overview"]
        assert overview["totalScrapers"] >= 1

    @pytest.mark.unit
    async def test_get_scrapers_success_rate_calculation(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_college,
    ):
        """Test that success rate is calculated correctly."""
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)

        # Create 7 successful and 3 failed runs (70% success rate)
        for i in range(7):
            log = ScraperLog(
                scraper_id=scraper.id,
                outcome="success",
                started_at=datetime.utcnow() - timedelta(days=i),
                completed_at=datetime.utcnow() - timedelta(days=i),
                duration_ms=1000,
            )
            test_db.add(log)

        for i in range(3):
            log = ScraperLog(
                scraper_id=scraper.id,
                outcome="error",
                started_at=datetime.utcnow() - timedelta(days=i),
                completed_at=datetime.utcnow() - timedelta(days=i),
            )
            test_db.add(log)
        test_db.commit()

        response = await admin_client.get("/api/admin/scrapers")
        data = response.json()["data"]
        overview = data["overview"]

        # Success rate should be 70%
        assert overview["successRate"] == pytest.approx(70.0, rel=0.1)

    @pytest.mark.unit
    async def test_get_scrapers_performance_trends(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_college,
    ):
        """Test performance trends aggregation."""
        scraper = Scraper(
            college_id=test_college.id,
            status="idle",
        )
        test_db.add(scraper)
        test_db.commit()
        test_db.refresh(scraper)

        # Create logs with different durations
        for i in range(5):
            log = ScraperLog(
                scraper_id=scraper.id,
                outcome="success",
                started_at=datetime.utcnow() - timedelta(days=1),
                completed_at=datetime.utcnow() - timedelta(days=1),
                duration_ms=float((i + 1) * 1000),
            )
            test_db.add(log)
        test_db.commit()

        response = await admin_client.get("/api/admin/scrapers?timeframe=7")
        data = response.json()["data"]

        assert len(data["performanceTrends"]) > 0

    @pytest.mark.unit
    async def test_get_scrapers_empty_data(
        self,
        admin_client: AsyncClient,
    ):
        """Test scrapers endpoint with no data."""
        response = await admin_client.get("/api/admin/scrapers")

        assert response.status_code == 200
        data = response.json()["data"]
        overview = data["overview"]
        assert overview["totalScrapers"] == 0
        assert overview["activeScrapers"] == 0
        assert overview["successRate"] == 0

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
        assert "users" in data
        assert "pagination" in data
        assert len(data["users"]) >= 1

        # Verify user structure
        user = data["users"][0]
        assert "id" in user
        assert "email" in user
        assert "role" in user

    @pytest.mark.unit
    async def test_get_users_pagination(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_college,
    ):
        """Test users pagination."""
        # Create multiple users with unique emails and UUIDs
        from uuid import uuid4
        from datetime import datetime

        timestamp = datetime.utcnow().timestamp()
        for i in range(15):
            user = Profile(
                id=uuid4(),
                email=f"test_pagination_{timestamp}_{i}@example.com",
                role="user",
                college_id=test_college.id,
            )
            test_db.add(user)
        test_db.commit()

        response = await admin_client.get("/api/admin/users?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["users"]) <= 10
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10

    @pytest.mark.unit
    async def test_get_users_search(
        self,
        admin_client: AsyncClient,
        test_user: Profile,
    ):
        """Test searching users by email."""
        search_term = test_user.email[:5]
        response = await admin_client.get(f"/api/admin/users?search={search_term}")

        assert response.status_code == 200
        data = response.json()["data"]
        for user in data["users"]:
            assert search_term.lower() in user["email"].lower()

    @pytest.mark.unit
    async def test_get_users_filter_by_role(
        self,
        admin_client: AsyncClient,
        test_admin_user: Profile,
    ):
        """Test filtering users by role."""
        response = await admin_client.get("/api/admin/users?role=admin")

        assert response.status_code == 200
        data = response.json()["data"]
        for user in data["users"]:
            assert user["role"] == "admin"

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
    async def test_get_user_invalid_uuid(
        self,
        admin_client: AsyncClient,
    ):
        """Test getting user with invalid UUID."""
        response = await admin_client.get("/api/admin/users/invalid-uuid")

        assert response.status_code == 422

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
        from models.college import College

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
            json={"collegeId": new_college.id},
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["collegeId"] == new_college.id

    @pytest.mark.unit
    async def test_update_user_multiple_fields(
        self,
        admin_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college,
    ):
        """Test updating multiple user fields at once."""
        response = await admin_client.patch(
            f"/api/admin/users/{test_user.id}",
            json={"role": "admin", "collegeId": test_college.id},
        )

        assert response.status_code == 200
        test_db.refresh(test_user)
        assert test_user.role == "admin"
        assert test_user.college_id == test_college.id

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
    async def test_update_user_invalid_role(
        self,
        admin_client: AsyncClient,
        test_user: Profile,
    ):
        """Test updating user with invalid role."""
        response = await admin_client.patch(
            f"/api/admin/users/{test_user.id}",
            json={"role": "superadmin"},  # Invalid role
        )

        assert response.status_code == 422

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

    @pytest.mark.unit
    async def test_update_user_empty_payload(
        self,
        admin_client: AsyncClient,
        test_user: Profile,
    ):
        """Test updating user with empty payload."""
        response = await admin_client.patch(
            f"/api/admin/users/{test_user.id}",
            json={},
        )

        assert response.status_code == 200
        # Should succeed but not change anything
