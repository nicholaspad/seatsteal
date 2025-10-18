"""Tests for notification API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from webapp.models.notification_log import NotificationLog
from webapp.models.subscription import Subscription


class TestGetNotificationTrends:
    """Tests for GET /api/notifications/trends endpoint."""

    @pytest.mark.unit
    async def test_get_notification_trends_success(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_subscription: Subscription,
    ):
        """Test successfully getting notification trends."""
        # Create some notification logs
        now = datetime.utcnow()
        for i in range(5):
            log = NotificationLog(
                subscription_id=test_subscription.id,
                college_id=test_subscription.college_id,
                notification_type="email",
                message="Test notification",
                status="sent",
                sent_at=now - timedelta(days=i),
            )
            test_db.add(log)
        await test_db.commit()

        response = await client.get("/api/notifications/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)

    @pytest.mark.unit
    async def test_get_notification_trends_empty(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
    ):
        """Test getting notification trends when no logs exist."""
        response = await client.get("/api/notifications/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0

    @pytest.mark.unit
    async def test_get_notification_trends_last_30_days(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_subscription: Subscription,
    ):
        """Test that trends only include last 30 days."""
        now = datetime.utcnow()

        # Create a recent log (within 30 days)
        recent_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            notification_type="email",
            message="Recent notification",
            status="sent",
            sent_at=now - timedelta(days=15),
        )
        test_db.add(recent_log)

        # Create an old log (more than 30 days)
        old_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            notification_type="email",
            message="Old notification",
            status="sent",
            sent_at=now - timedelta(days=35),
        )
        test_db.add(old_log)
        await test_db.commit()

        response = await client.get("/api/notifications/trends")

        assert response.status_code == 200
        data = response.json()

        # Check that dates are within the last 30 days
        for trend in data["data"]:
            if trend["date"]:
                trend_date = datetime.fromisoformat(trend["date"])
                assert (now - trend_date).days <= 30
