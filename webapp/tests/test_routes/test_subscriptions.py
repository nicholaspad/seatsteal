"""Tests for subscription API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.user import Profile
from models.class_model import Class
from models.subscription import Subscription
from models.college import College


class TestGetSubscriptions:
    """Tests for GET /api/subscriptions/ endpoint."""

    @pytest.mark.unit
    async def test_get_subscriptions_success(
        self,
        authenticated_client: AsyncClient,
        test_subscription: Subscription,
        test_class: Class,
        test_course,
        test_college: College,
    ):
        """Test successfully getting user subscriptions."""
        response = await authenticated_client.get("/api/subscriptions/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) == 1
        assert data[0]["id"] == test_subscription.id
        assert data[0]["classId"] == test_class.class_id
        assert data[0]["isActive"] is True

    @pytest.mark.unit
    async def test_get_subscriptions_empty(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test getting subscriptions when user has none."""
        response = await authenticated_client.get("/api/subscriptions/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) == 0

    @pytest.mark.unit
    async def test_get_subscriptions_only_active(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college: College,
    ):
        """Test that only active subscriptions are returned."""
        # Create active subscription
        active_sub = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
            notification_count=0,
        )
        test_db.add(active_sub)

        # Create inactive subscription
        inactive_sub = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=False,
            notification_count=0,
        )
        test_db.add(inactive_sub)
        test_db.commit()

        response = await authenticated_client.get("/api/subscriptions/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data) == 1
        assert data[0]["isActive"] is True

    @pytest.mark.unit
    async def test_get_subscriptions_unauthenticated(self, client: AsyncClient):
        """Test getting subscriptions without authentication."""
        response = await client.get("/api/subscriptions/")

        assert response.status_code == 401


class TestCreateSubscription:
    """Tests for POST /api/subscriptions/ endpoint."""

    @pytest.mark.unit
    async def test_create_subscription_success(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_class: Class,
        test_college: College,
    ):
        """Test successfully creating a subscription."""
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={
                "classId": test_class.class_id,
                "collegeId": test_college.id,
            },
        )

        assert response.status_code == 201
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["classId"] == test_class.class_id
        assert data["userId"] == str(test_user.id)
        assert data["isActive"] is True
        assert data["notificationCount"] == 0

        # Verify in database
        result = test_db.execute(
            select(Subscription).where(Subscription.id == data["id"])
        )
        subscription = result.scalar_one_or_none()
        assert subscription is not None

    @pytest.mark.unit
    async def test_create_subscription_duplicate(
        self,
        authenticated_client: AsyncClient,
        test_subscription: Subscription,
    ):
        """Test creating duplicate subscription returns 409."""
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={
                "classId": test_subscription.class_id,
                "collegeId": test_subscription.college_id,
            },
        )

        assert response.status_code == 409
        assert "Already subscribed" in response.json()["detail"]

    @pytest.mark.unit
    async def test_create_subscription_invalid_class(
        self,
        authenticated_client: AsyncClient,
        test_college: College,
    ):
        """Test creating subscription with invalid class."""
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={
                "classId": 99999,
                "collegeId": test_college.id,
            },
        )

        assert response.status_code == 404
        assert "Class not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_create_subscription_unauthenticated(self, client: AsyncClient):
        """Test creating subscription without authentication."""
        response = await client.post(
            "/api/subscriptions/",
            json={"classId": 1, "collegeId": 1},
        )

        assert response.status_code == 401


class TestDeleteSubscription:
    """Tests for DELETE /api/subscriptions/{subscription_id} endpoint."""

    @pytest.mark.unit
    async def test_delete_subscription_success(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_subscription: Subscription,
    ):
        """Test successfully deleting a subscription."""
        response = await authenticated_client.delete(
            f"/api/subscriptions/{test_subscription.id}"
        )

        assert response.status_code == 204

        # Verify subscription is deactivated
        test_db.refresh(test_subscription)
        assert test_subscription.is_active is False

    @pytest.mark.unit
    async def test_delete_subscription_not_found(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test deleting non-existent subscription."""
        response = await authenticated_client.delete("/api/subscriptions/99999")

        assert response.status_code == 404
        assert "Subscription not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_delete_subscription_wrong_user(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        """Test deleting another user's subscription."""
        # Create another user
        from uuid import uuid4

        other_user = Profile(
            id=str(uuid4()),
            email="other@example.edu",
            phone="+1111111111",
            college_id=test_college.id,
            role="user",
        )
        test_db.add(other_user)
        test_db.commit()

        # Create class
        from models.course import Course

        course = Course(
            college_id=test_college.id,
            course_code="CS200",
            title="Test Course",
            is_active=True,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        other_class = Class(
            course_id=course.id,
            class_number="99999",
            section_code="Z",
            is_active=True,
        )
        test_db.add(other_class)
        test_db.commit()
        test_db.refresh(other_class)

        # Create subscription for other user
        other_subscription = Subscription(
            user_id=other_user.id,
            class_id=other_class.class_id,
            college_id=test_college.id,
            is_active=True,
            notification_count=0,
        )
        test_db.add(other_subscription)
        test_db.commit()
        test_db.refresh(other_subscription)

        response = await authenticated_client.delete(
            f"/api/subscriptions/{other_subscription.id}"
        )

        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    @pytest.mark.unit
    async def test_delete_subscription_unauthenticated(self, client: AsyncClient):
        """Test deleting subscription without authentication."""
        response = await client.delete("/api/subscriptions/1")

        assert response.status_code == 401
