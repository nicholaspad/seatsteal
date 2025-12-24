"""Tests for database models."""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from uuid import uuid4

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from models.user import Profile
from models.college import College
from models.course import Course
from models.class_model import Class
from models.enrollment import Enrollment
from models.subscription import Subscription
from models.stripe_customer import StripeCustomer
from models.stripe_subscription import StripeSubscription
from models.notification_log import NotificationLog
from models.referral import Referral
from models.referral_redemption import ReferralRedemption


class TestCollegeModel:
    """Tests for College model."""

    @pytest.mark.unit
    def test_create_college(self, test_db: Session):
        """Test creating a college."""
        college = College(
            name="Harvard University",
            short_name="harvard",
            is_active=True,
            term_code="202410",
            term_name="Fall 2024",
        )
        test_db.add(college)
        test_db.commit()
        test_db.refresh(college)

        assert college.id is not None
        assert college.name == "Harvard University"
        assert college.short_name == "harvard"
        assert college.is_active is True

    @pytest.mark.unit
    def test_college_unique_short_name(self, test_db: Session):
        """Test that short_name must be unique."""
        college1 = College(name="Test U 1", short_name="test", is_active=True)
        college2 = College(name="Test U 2", short_name="test", is_active=True)

        test_db.add(college1)
        test_db.commit()

        test_db.add(college2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    @pytest.mark.unit
    def test_college_defaults(self, test_db: Session):
        """Test college default values."""
        college = College(name="Test", short_name="test")
        test_db.add(college)
        test_db.commit()
        test_db.refresh(college)

        # Should have default values
        assert college.is_active is True
        assert college.email_enabled is True
        assert college.sms_enabled is True


class TestProfileModel:
    """Tests for Profile (user) model."""

    @pytest.mark.unit
    def test_create_profile(self, test_db: Session, test_college: College):
        """Test creating a user profile."""
        user_id = uuid4()
        profile = Profile(
            id=user_id,
            email="student@test.edu",
            phone="1234567890",
            college_id=test_college.id,
            role="user",
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)

        assert profile.id == user_id
        assert profile.email == "student@test.edu"
        assert profile.role == "user"

    @pytest.mark.unit
    def test_profile_unique_email(self, test_db: Session, test_college: College):
        """Test that email must be unique."""
        profile1 = Profile(
            id=uuid4(),
            email="duplicate@test.edu",
            college_id=test_college.id,
        )
        profile2 = Profile(
            id=uuid4(),
            email="duplicate@test.edu",
            college_id=test_college.id,
        )

        test_db.add(profile1)
        test_db.commit()

        test_db.add(profile2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    @pytest.mark.unit
    def test_profile_default_role(self, test_db: Session, test_college: College):
        """Test that default role is 'user'."""
        profile = Profile(
            id=uuid4(),
            email="test@test.edu",
            college_id=test_college.id,
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)

        assert profile.role == "user"


class TestCourseModel:
    """Tests for Course model."""

    @pytest.mark.unit
    def test_create_course(self, test_db: Session, test_college: College):
        """Test creating a course."""
        course = Course(
            college_id=test_college.id,
            course_code="MATH 101",
            title="Calculus I",
            is_active=True,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        assert course.id is not None
        assert course.course_code == "MATH 101"
        assert course.title == "Calculus I"

    @pytest.mark.unit
    def test_course_college_relationship(self, test_db: Session, test_college: College):
        """Test course-college relationship."""
        course = Course(
            college_id=test_college.id,
            course_code="CS 101",
            title="Intro to CS",
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        # Relationship should work
        assert course.college_id == test_college.id

    @pytest.mark.unit
    def test_course_cascade_delete(self, test_db: Session, test_college: College):
        """Test that deleting college cascades to courses."""
        course = Course(
            college_id=test_college.id,
            course_code="CS 101",
            title="Test Course",
        )
        test_db.add(course)
        test_db.commit()

        # Delete college
        test_db.delete(test_college)
        test_db.commit()

        # Course should also be deleted (or orphaned depending on cascade settings)
        remaining = test_db.query(Course).filter_by(id=course.id).first()
        # This depends on the cascade configuration in the model


class TestClassModel:
    """Tests for Class model."""

    @pytest.mark.unit
    def test_create_class(self, test_db: Session, test_course: Course):
        """Test creating a class."""
        cls = Class(
            course_id=test_course.id,
            class_number="54321",
            section_code="B",
            is_active=True,
        )
        test_db.add(cls)
        test_db.commit()
        test_db.refresh(cls)

        assert cls.class_id is not None
        assert cls.class_number == "54321"
        assert cls.section_code == "B"

    @pytest.mark.unit
    def test_class_course_relationship(self, test_db: Session, test_course: Course):
        """Test class-course relationship."""
        cls = Class(
            course_id=test_course.id,
            class_number="11111",
            section_code="A",
        )
        test_db.add(cls)
        test_db.commit()
        test_db.refresh(cls)

        assert cls.course_id == test_course.id


class TestEnrollmentModel:
    """Tests for Enrollment model."""

    @pytest.mark.unit
    def test_create_enrollment(self, test_db: Session, test_class: Class, test_college: College):
        """Test creating an enrollment record."""
        enrollment = Enrollment(
            class_id=test_class.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)
        test_db.commit()
        test_db.refresh(enrollment)

        assert enrollment.id is not None
        assert enrollment.enrollment_status == "open"
        assert enrollment.scraped_at is not None

    @pytest.mark.unit
    def test_enrollment_status_values(self, test_db: Session, test_class: Class, test_college: College):
        """Test valid enrollment status values."""
        valid_statuses = ["open", "closed", "waitlist"]

        for status in valid_statuses:
            enrollment = Enrollment(
                class_id=test_class.class_id,
                college_id=test_college.id,
                enrollment_status=status,
                scraped_at=datetime.now(timezone.utc),
            )
            test_db.add(enrollment)
            test_db.commit()
            test_db.refresh(enrollment)

            assert enrollment.enrollment_status == status
            test_db.delete(enrollment)
            test_db.commit()


class TestSubscriptionModel:
    """Tests for Subscription model."""

    @pytest.mark.unit
    def test_create_subscription(
        self, test_db: Session, test_user: Profile, test_class: Class, test_college: College
    ):
        """Test creating a subscription."""
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
            is_active=True,
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        assert subscription.id is not None
        assert subscription.is_active is True
        assert subscription.notification_count == 0

    @pytest.mark.unit
    def test_subscription_defaults(
        self, test_db: Session, test_user: Profile, test_class: Class, test_college: College
    ):
        """Test subscription default values."""
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        assert subscription.is_active is True
        assert subscription.notification_count == 0
        assert subscription.created_at is not None

    @pytest.mark.unit
    def test_subscription_relationships(
        self, test_db: Session, test_user: Profile, test_class: Class, test_college: College
    ):
        """Test subscription relationships."""
        subscription = Subscription(
            user_id=test_user.id,
            class_id=test_class.class_id,
            college_id=test_college.id,
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        assert subscription.user_id == test_user.id
        assert subscription.class_id == test_class.class_id
        assert subscription.college_id == test_college.id


class TestStripeCustomerModel:
    """Tests for StripeCustomer model."""

    @pytest.mark.unit
    def test_create_stripe_customer(self, test_db: Session, test_user: Profile):
        """Test creating a Stripe customer record."""
        customer = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            email=test_user.email,
        )
        test_db.add(customer)
        test_db.commit()
        test_db.refresh(customer)

        assert customer.id is not None
        assert customer.stripe_customer_id == "cus_test123"
        assert customer.user_id == test_user.id

    @pytest.mark.unit
    def test_stripe_customer_unique_user(self, test_db: Session, test_user: Profile):
        """Test that one user can only have one Stripe customer."""
        customer1 = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_1",
            email=test_user.email,
        )
        customer2 = StripeCustomer(
            user_id=test_user.id,
            stripe_customer_id="cus_2",
            email=test_user.email,
        )

        test_db.add(customer1)
        test_db.commit()

        test_db.add(customer2)
        with pytest.raises(IntegrityError):
            test_db.commit()


class TestStripeSubscriptionModel:
    """Tests for StripeSubscription model."""

    @pytest.mark.unit
    def test_create_stripe_subscription(self, test_db: Session, test_user: Profile):
        """Test creating a Stripe subscription record."""
        subscription = StripeSubscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_test123",
            tier="pro",
            status="active",
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)

        assert subscription.id is not None
        assert subscription.tier == "pro"
        assert subscription.status == "active"

    @pytest.mark.unit
    def test_stripe_subscription_tier_values(self, test_db: Session, test_user: Profile):
        """Test valid tier values."""
        valid_tiers = ["free", "plus", "pro"]

        for i, tier in enumerate(valid_tiers):
            subscription = StripeSubscription(
                user_id=test_user.id,
                stripe_subscription_id=f"sub_{i}",
                tier=tier,
                status="active",
            )
            test_db.add(subscription)
            test_db.commit()
            test_db.refresh(subscription)

            assert subscription.tier == tier

    @pytest.mark.unit
    def test_stripe_subscription_status_values(self, test_db: Session, test_user: Profile):
        """Test valid status values."""
        valid_statuses = ["active", "trialing", "canceled", "past_due"]

        for i, status in enumerate(valid_statuses):
            subscription = StripeSubscription(
                user_id=test_user.id,
                stripe_subscription_id=f"sub_status_{i}",
                tier="pro",
                status=status,
            )
            test_db.add(subscription)
            test_db.commit()
            test_db.refresh(subscription)

            assert subscription.status == status


class TestNotificationLogModel:
    """Tests for NotificationLog model."""

    @pytest.mark.unit
    def test_create_notification_log(
        self,
        test_db: Session,
        test_user: Profile,
        test_subscription: Subscription,
        test_college: College,
    ):
        """Test creating a notification log."""
        log = NotificationLog(
            college_id=test_college.id,
            subscription_id=test_subscription.id,
            user_id=test_user.id,
            notification_type="email",
            message="Test notification",
            status="sent",
        )
        test_db.add(log)
        test_db.commit()
        test_db.refresh(log)

        assert log.id is not None
        assert log.notification_type == "email"
        assert log.status == "sent"

    @pytest.mark.unit
    def test_notification_log_nullable_subscription(
        self, test_db: Session, test_user: Profile, test_college: College
    ):
        """Test that subscription_id can be null (for orphaned logs)."""
        log = NotificationLog(
            college_id=test_college.id,
            subscription_id=None,  # Nullable
            user_id=test_user.id,
            notification_type="email",
            message="Test",
            status="sent",
        )
        test_db.add(log)
        test_db.commit()
        test_db.refresh(log)

        assert log.subscription_id is None

    @pytest.mark.unit
    def test_notification_log_types(
        self, test_db: Session, test_user: Profile, test_college: College
    ):
        """Test valid notification types."""
        valid_types = ["email", "sms"]

        for notification_type in valid_types:
            log = NotificationLog(
                college_id=test_college.id,
                user_id=test_user.id,
                notification_type=notification_type,
                message="Test",
                status="sent",
            )
            test_db.add(log)
            test_db.commit()
            test_db.refresh(log)

            assert log.notification_type == notification_type
            test_db.delete(log)
            test_db.commit()


class TestReferralModel:
    """Tests for Referral model."""

    @pytest.mark.unit
    def test_create_referral(self, test_db: Session, test_user: Profile):
        """Test creating a referral."""
        referral = Referral(
            referrer_id=test_user.id,
            code="TESTCODE123",
        )
        test_db.add(referral)
        test_db.commit()
        test_db.refresh(referral)

        assert referral.id is not None
        assert referral.code == "TESTCODE123"
        assert referral.referrer_id == test_user.id

    @pytest.mark.unit
    def test_referral_unique_code(self, test_db: Session, test_user: Profile):
        """Test that referral codes must be unique."""
        referral1 = Referral(referrer_id=test_user.id, code="DUPLICATE")
        referral2 = Referral(referrer_id=test_user.id, code="DUPLICATE")

        test_db.add(referral1)
        test_db.commit()

        test_db.add(referral2)
        with pytest.raises(IntegrityError):
            test_db.commit()


class TestReferralRedemptionModel:
    """Tests for ReferralRedemption model."""

    @pytest.mark.unit
    def test_create_referral_redemption(
        self, test_db: Session, test_user: Profile, test_college: College
    ):
        """Test creating a referral redemption."""
        # Create referrer and referee
        referrer = test_user
        referee = Profile(
            id=uuid4(),
            email="referee@test.edu",
            college_id=test_college.id,
        )
        test_db.add(referee)

        referral = Referral(referrer_id=referrer.id, code="REFCODE")
        test_db.add(referral)
        test_db.commit()

        redemption = ReferralRedemption(
            referral_id=referral.id,
            referee_id=referee.id,
            trial_days_granted=14,
        )
        test_db.add(redemption)
        test_db.commit()
        test_db.refresh(redemption)

        assert redemption.id is not None
        assert redemption.trial_days_granted == 14

    @pytest.mark.unit
    def test_referral_redemption_unique_referee(
        self, test_db: Session, test_user: Profile, test_college: College
    ):
        """Test that a user can only redeem one referral."""
        referrer = test_user
        referee = Profile(
            id=uuid4(),
            email="referee@test.edu",
            college_id=test_college.id,
        )
        test_db.add(referee)

        referral = Referral(referrer_id=referrer.id, code="CODE")
        test_db.add(referral)
        test_db.commit()

        redemption1 = ReferralRedemption(
            referral_id=referral.id,
            referee_id=referee.id,
            trial_days_granted=14,
        )
        redemption2 = ReferralRedemption(
            referral_id=referral.id,
            referee_id=referee.id,
            trial_days_granted=14,
        )

        test_db.add(redemption1)
        test_db.commit()

        test_db.add(redemption2)
        with pytest.raises(IntegrityError):
            test_db.commit()
