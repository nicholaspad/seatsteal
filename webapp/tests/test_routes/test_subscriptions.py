"""Tests for subscription API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.user import Profile
from models.class_model import Class
from models.course import Course
from models.subscription import Subscription
from models.college import College
from models.stripe_subscription import StripeSubscription
from models.stripe_customer import StripeCustomer


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
            phone="1111111111",
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


class TestSubscriptionLimits:
    """Tests for subscription limit enforcement."""

    @pytest.mark.unit
    async def test_free_tier_limit_enforced(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college: College,
    ):
        """Test that free tier users cannot exceed 1 subscription."""
        # Create a course and class
        course = Course(
            college_id=test_college.id,
            course_code="CS101",
            title="Test Course",
            is_active=True,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        class1 = Class(
            course_id=course.id,
            class_number="11111",
            section_code="A",
            is_active=True,
        )
        class2 = Class(
            course_id=course.id,
            class_number="22222",
            section_code="B",
            is_active=True,
        )
        test_db.add_all([class1, class2])
        test_db.commit()
        test_db.refresh(class1)
        test_db.refresh(class2)

        # First subscription should succeed (free tier limit is 1)
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={"classId": class1.class_id, "collegeId": test_college.id},
        )
        assert response.status_code == 201

        # Second subscription should fail
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={"classId": class2.class_id, "collegeId": test_college.id},
        )
        assert response.status_code == 400
        assert "subscription limit" in response.json()["detail"]

    @pytest.mark.unit
    async def test_plus_tier_limit_enforced(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college: College,
    ):
        """Test that plus tier users cannot exceed 5 subscriptions."""
        # Create Stripe customer first
        stripe_customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test_plus",
            email=test_user.email,
        )
        test_db.add(stripe_customer)
        test_db.commit()

        # Create a Stripe subscription for plus tier
        stripe_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_test_plus",
            stripe_customer_id="cus_test_plus",
            status="active",
            price_id="price_plus",
            tier="plus",
        )
        test_db.add(stripe_sub)
        test_db.commit()

        # Create a course and 6 classes
        course = Course(
            college_id=test_college.id,
            course_code="CS200",
            title="Test Course",
            is_active=True,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        classes = []
        for i in range(6):
            c = Class(
                course_id=course.id,
                class_number=f"3{i}000",
                section_code=chr(65 + i),
                is_active=True,
            )
            test_db.add(c)
            classes.append(c)
        test_db.commit()
        for c in classes:
            test_db.refresh(c)

        # First 5 subscriptions should succeed (plus tier limit is 5)
        for i in range(5):
            response = await authenticated_client.post(
                "/api/subscriptions/",
                json={"classId": classes[i].class_id, "collegeId": test_college.id},
            )
            assert response.status_code == 201, f"Subscription {i+1} should succeed"

        # 6th subscription should fail
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={"classId": classes[5].class_id, "collegeId": test_college.id},
        )
        assert response.status_code == 400
        assert "subscription limit" in response.json()["detail"]

    @pytest.mark.unit
    async def test_pro_tier_allows_up_to_20_subscriptions(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college: College,
    ):
        """Test that pro tier users can subscribe to up to 20 classes."""
        # Create Stripe customer first
        stripe_customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test_pro",
            email=test_user.email,
        )
        test_db.add(stripe_customer)
        test_db.commit()

        # Create a Stripe subscription for pro tier
        stripe_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_test_pro",
            stripe_customer_id="cus_test_pro",
            status="active",
            price_id="price_pro",
            tier="pro",
        )
        test_db.add(stripe_sub)
        test_db.commit()

        # Create a course and 21 classes
        course = Course(
            college_id=test_college.id,
            course_code="CS300",
            title="Test Course",
            is_active=True,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        classes = []
        for i in range(21):
            c = Class(
                course_id=course.id,
                class_number=f"4{i:02d}00",
                section_code=f"S{i}",
                is_active=True,
            )
            test_db.add(c)
            classes.append(c)
        test_db.commit()
        for c in classes:
            test_db.refresh(c)

        # First 20 subscriptions should succeed (pro tier limit is 20)
        for i in range(20):
            response = await authenticated_client.post(
                "/api/subscriptions/",
                json={"classId": classes[i].class_id, "collegeId": test_college.id},
            )
            assert response.status_code == 201, f"Subscription {i+1} should succeed"

        # 21st subscription should fail
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={"classId": classes[20].class_id, "collegeId": test_college.id},
        )
        assert response.status_code == 400
        assert "subscription limit" in response.json()["detail"]

    @pytest.mark.unit
    async def test_unsubscribe_allows_new_subscription(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_college: College,
    ):
        """Test that unsubscribing allows subscribing to a new class."""
        # Create a course and 2 classes
        course = Course(
            college_id=test_college.id,
            course_code="CS400",
            title="Test Course",
            is_active=True,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        class1 = Class(
            course_id=course.id,
            class_number="50001",
            section_code="A",
            is_active=True,
        )
        class2 = Class(
            course_id=course.id,
            class_number="50002",
            section_code="B",
            is_active=True,
        )
        test_db.add_all([class1, class2])
        test_db.commit()
        test_db.refresh(class1)
        test_db.refresh(class2)

        # Subscribe to first class
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={"classId": class1.class_id, "collegeId": test_college.id},
        )
        assert response.status_code == 201
        sub_id = response.json()["data"]["id"]

        # Try to subscribe to second class (should fail - free tier limit is 1)
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={"classId": class2.class_id, "collegeId": test_college.id},
        )
        assert response.status_code == 400

        # Unsubscribe from first class
        response = await authenticated_client.delete(f"/api/subscriptions/{sub_id}")
        assert response.status_code == 204

        # Now subscribing to second class should succeed
        response = await authenticated_client.post(
            "/api/subscriptions/",
            json={"classId": class2.class_id, "collegeId": test_college.id},
        )
        assert response.status_code == 201


class TestSubscriptionStatus:
    """Tests for GET /api/subscriptions/status endpoint."""

    @pytest.mark.unit
    async def test_get_status_free_tier(
        self,
        authenticated_client: AsyncClient,
        test_user: Profile,
    ):
        """Test getting subscription status for free tier user."""
        response = await authenticated_client.get("/api/subscriptions/status")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["currentCount"] == 0
        assert data["maxSubscriptions"] == 1
        assert data["tier"] == "free"
        assert data["canSubscribe"] is True

    @pytest.mark.unit
    async def test_get_status_with_subscriptions(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
        test_subscription: Subscription,
    ):
        """Test getting subscription status with active subscriptions."""
        response = await authenticated_client.get("/api/subscriptions/status")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["currentCount"] == 1
        assert data["maxSubscriptions"] == 1
        assert data["tier"] == "free"
        assert data["canSubscribe"] is False  # At limit

    @pytest.mark.unit
    async def test_get_status_plus_tier(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test getting subscription status for plus tier user."""
        # Create Stripe customer first
        stripe_customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_status_plus",
            email=test_user.email,
        )
        test_db.add(stripe_customer)
        test_db.commit()

        # Create a Stripe subscription for plus tier
        stripe_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_test_plus",
            stripe_customer_id="cus_status_plus",
            status="active",
            price_id="price_plus",
            tier="plus",
        )
        test_db.add(stripe_sub)
        test_db.commit()

        response = await authenticated_client.get("/api/subscriptions/status")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["currentCount"] == 0
        assert data["maxSubscriptions"] == 5
        assert data["tier"] == "plus"
        assert data["canSubscribe"] is True

    @pytest.mark.unit
    async def test_get_status_pro_tier(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_user: Profile,
    ):
        """Test getting subscription status for pro tier user."""
        # Create Stripe customer first
        stripe_customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_status_pro",
            email=test_user.email,
        )
        test_db.add(stripe_customer)
        test_db.commit()

        # Create a Stripe subscription for pro tier
        stripe_sub = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_test_pro",
            stripe_customer_id="cus_status_pro",
            status="active",
            price_id="price_pro",
            tier="pro",
        )
        test_db.add(stripe_sub)
        test_db.commit()

        response = await authenticated_client.get("/api/subscriptions/status")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["currentCount"] == 0
        assert data["maxSubscriptions"] == 20
        assert data["tier"] == "pro"
        assert data["canSubscribe"] is True

    @pytest.mark.unit
    async def test_get_status_unauthenticated(self, client: AsyncClient):
        """Test getting subscription status without authentication."""
        response = await client.get("/api/subscriptions/status")

        assert response.status_code == 401
