"""Tests for notification API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from models.notification_log import NotificationLog
from models.subscription import Subscription
from models.user import Profile


class TestGetNotificationTrends:
    """Tests for GET /api/notifications/trends endpoint."""

    @pytest.mark.unit
    async def test_get_notification_trends_requires_auth(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test that trends endpoint requires authentication."""
        response = await client.get("/api/notifications/trends")

        assert response.status_code == 401

    @pytest.mark.unit
    async def test_get_notification_trends_success(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
    ):
        """Test successfully getting notification trends."""
        # Create some notification logs for the past 7 days
        now = datetime.now(timezone.utc)
        # Start from 6 days ago (rolling 7-day window)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        for i in range(3):
            log = NotificationLog(
                subscription_id=test_subscription.id,
                college_id=test_subscription.college_id,
                user_id=test_user.id,
                notification_type="email",
                message="Introduction to CS (CS101) A at Test University is OPEN!",
                status="sent",
                sent_at=start_date + timedelta(days=i),
            )
            test_db.add(log)
        test_db.commit()

        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert isinstance(data, list)
        assert len(data) == 7  # 7 days

        # Check structure of each day
        for day_data in data:
            assert "date" in day_data
            assert "notifications" in day_data
            assert "courses" in day_data
            assert isinstance(day_data["notifications"], int)
            assert isinstance(day_data["courses"], list)
            # Verify date format (ISO: YYYY-MM-DD)
            from datetime import date

            date.fromisoformat(day_data["date"])  # Should not raise

    @pytest.mark.unit
    async def test_get_notification_trends_empty(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test getting notification trends when no logs exist."""
        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) == 7  # Still returns 7 days

        # All days should have 0 notifications
        for day_data in data:
            assert day_data["notifications"] == 0
            assert day_data["courses"] == []

    @pytest.mark.unit
    async def test_get_notification_trends_only_past_7_days(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
    ):
        """Test that trends only include the past 7 days (rolling window)."""
        now = datetime.now(timezone.utc)

        # Start from 6 days ago (rolling 7-day window)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Create a log from within the 7-day window
        recent_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,
            notification_type="email",
            message="Recent Course (RECENT101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=2),  # 4 days ago
        )
        test_db.add(recent_log)

        # Create an old log (outside the 7-day window)
        old_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,
            notification_type="email",
            message="Old Course (OLD101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date - timedelta(days=1),  # 8 days ago
        )
        test_db.add(old_log)
        test_db.commit()

        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]

        # Total notifications should be 1 (only the recent one)
        total_notifications = sum(d["notifications"] for d in data)
        assert total_notifications == 1

        # Find the day with notifications
        notification_day = [d for d in data if d["notifications"] > 0][0]
        assert notification_day["notifications"] == 1
        assert len(notification_day["courses"]) == 1
        assert "Recent Course" in notification_day["courses"][0]

    @pytest.mark.unit
    async def test_get_notification_trends_only_user_subscriptions(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
        test_class,
        test_college,
    ):
        """Test that trends only include user's own subscriptions."""
        from uuid import uuid4

        now = datetime.now(timezone.utc)
        # Start from 6 days ago (rolling 7-day window)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Create another user and their subscription
        other_user = Profile(
            id=uuid4(),
            email="other@example.edu",
            phone="9876543210",
            college_id=test_college.id,
            role="user",
        )
        test_db.add(other_user)
        test_db.commit()
        test_db.refresh(other_user)

        from models.subscription import Subscription as SubscriptionModel

        other_subscription = SubscriptionModel(
            user_id=other_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
            notification_count=0,
        )
        test_db.add(other_subscription)
        test_db.commit()
        test_db.refresh(other_subscription)

        # Create log for current user
        user_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,
            notification_type="email",
            message="My Course (MY101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=2),  # 4 days ago
        )
        test_db.add(user_log)

        # Create log for other user
        other_log = NotificationLog(
            subscription_id=other_subscription.id,
            college_id=other_subscription.college_id,
            user_id=other_user.id,
            notification_type="email",
            message="Other Course (OTHER101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=2),  # Same day
        )
        test_db.add(other_log)
        test_db.commit()

        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        data = response_json["data"]

        # Total should be 1 (only current user's notification)
        total_notifications = sum(d["notifications"] for d in data)
        assert total_notifications == 1

        # Should only see the current user's course
        all_courses = []
        for day_data in data:
            all_courses.extend(day_data["courses"])
        assert len(all_courses) == 1
        assert "My Course" in all_courses[0]
        assert "Other Course" not in str(all_courses)

    @pytest.mark.unit
    async def test_get_notification_trends_excludes_failed(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
    ):
        """Test that trends only include successful notifications."""
        now = datetime.now(timezone.utc)
        # Start from 6 days ago (rolling 7-day window)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Create a successful notification
        success_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,
            notification_type="email",
            message="Success Course (SUCCESS101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=1),
        )
        test_db.add(success_log)

        # Create a failed notification
        failed_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,
            notification_type="email",
            message="Failed Course (FAIL101) A at Test University is OPEN!",
            status="failed",
            sent_at=start_date + timedelta(days=1),
        )
        test_db.add(failed_log)
        test_db.commit()

        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        data = response_json["data"]

        # Total should be 1 (only successful notification)
        total_notifications = sum(d["notifications"] for d in data)
        assert total_notifications == 1

    @pytest.mark.unit
    async def test_get_notification_trends_counts_both_email_and_sms(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
    ):
        """Test that both email and SMS notifications are counted separately."""
        now = datetime.now(timezone.utc)
        # Start from 6 days ago (rolling 7-day window)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Create email notification
        email_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,
            notification_type="email",
            message="Course (CS101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=1),
        )
        test_db.add(email_log)

        # Create SMS notification for the same course
        sms_log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,
            notification_type="sms",
            message="Course (CS101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=1),
        )
        test_db.add(sms_log)
        test_db.commit()

        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        data = response_json["data"]

        # Total should be 2 (both email and SMS counted)
        total_notifications = sum(d["notifications"] for d in data)
        assert total_notifications == 2

        # But courses should be deduplicated (same course for both)
        # Find the day with notifications
        notification_day = [d for d in data if d["notifications"] > 0][0]
        assert notification_day["notifications"] == 2
        assert len(notification_day["courses"]) == 1  # Course only listed once

    @pytest.mark.unit
    async def test_get_notification_trends_with_null_subscription(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college,
    ):
        """Test that trends work when subscription_id is NULL but user_id is set."""
        now = datetime.now(timezone.utc)
        # Start from 6 days ago (rolling 7-day window)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Create a log with user_id but NULL subscription_id (simulates deleted subscription)
        log = NotificationLog(
            subscription_id=None,  # Subscription was deleted
            college_id=test_college.id,
            user_id=test_user.id,  # But user_id is preserved
            notification_type="email",
            message="Orphan Course (ORPHAN101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=1),
        )
        test_db.add(log)
        test_db.commit()

        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        data = response_json["data"]

        # Should still find the notification via user_id
        total_notifications = sum(d["notifications"] for d in data)
        assert total_notifications == 1

        # Find the day with notifications
        notification_day = [d for d in data if d["notifications"] > 0][0]
        assert notification_day["notifications"] == 1
        assert "Orphan Course" in notification_day["courses"][0]

    @pytest.mark.unit
    async def test_get_notification_trends_uuid_casting(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
        test_user: Profile,
    ):
        """Test that UUID casting works correctly in the trends query."""
        now = datetime.now(timezone.utc)
        # Start from 6 days ago (rolling 7-day window)
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Create notification log with explicit user_id
        log = NotificationLog(
            subscription_id=test_subscription.id,
            college_id=test_subscription.college_id,
            user_id=test_user.id,  # UUID type
            notification_type="email",
            message="UUID Test Course (UUID101) A at Test University is OPEN!",
            status="sent",
            sent_at=start_date + timedelta(days=1),
        )
        test_db.add(log)
        test_db.commit()

        response = await authenticated_client.get("/api/notifications/trends")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]

        # Should find the notification despite UUID type comparison
        total_notifications = sum(d["notifications"] for d in data)
        assert total_notifications == 1

        # Find the day with notifications
        notification_day = [d for d in data if d["notifications"] > 0][0]
        assert notification_day["notifications"] == 1
        assert any(
            "UUID Test Course" in course for course in notification_day["courses"]
        )
