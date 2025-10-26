"""Tests for notification API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.notification_log import NotificationLog
from models.subscription import Subscription


class TestGetNotificationTrends:
    """Tests for GET /api/notifications/trends endpoint."""

    @pytest.mark.unit
    async def test_get_notification_trends_success(
        self,
        client: AsyncClient,
        test_db: Session,
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
        test_db.commit()

        response = await client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert isinstance(data, list)

    @pytest.mark.unit
    async def test_get_notification_trends_empty(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test getting notification trends when no logs exist."""
        response = await client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) == 0

    @pytest.mark.unit
    async def test_get_notification_trends_last_30_days(
        self,
        client: AsyncClient,
        test_db: Session,
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
        test_db.commit()

        response = await client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]

        # Check that dates are within the last 30 days
        for trend in data:
            if trend["date"]:
                trend_date = datetime.fromisoformat(trend["date"])
                assert (now - trend_date).days <= 30
