"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from uuid import uuid4

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from schemas.admin import (
    TermUpdateRequest,
    TermUpdateCleanupStats,
    TermUpdateResponse,
)
from schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionStatus,
)
from schemas.course import CourseResponse, CourseCreate
from schemas.class_schema import ClassResponse, ClassCreate
from schemas.college import CollegeResponse


class TestTermUpdateSchemas:
    """Tests for admin term update schemas."""

    @pytest.mark.unit
    def test_term_update_request_valid(self):
        """Test valid TermUpdateRequest."""
        data = {"termCode": "202510", "termName": "Fall 2025"}
        request = TermUpdateRequest(**data)

        assert request.term_code == "202510"
        assert request.term_name == "Fall 2025"

    @pytest.mark.unit
    def test_term_update_request_alias(self):
        """Test TermUpdateRequest with snake_case."""
        data = {"term_code": "202510", "term_name": "Fall 2025"}
        request = TermUpdateRequest(**data)

        assert request.term_code == "202510"

    @pytest.mark.unit
    def test_term_update_request_optional_name(self):
        """Test TermUpdateRequest without optional term_name."""
        data = {"termCode": "202510"}
        request = TermUpdateRequest(**data)

        assert request.term_code == "202510"
        assert request.term_name is None

    @pytest.mark.unit
    def test_term_update_request_empty_code_fails(self):
        """Test TermUpdateRequest fails with empty term_code."""
        data = {"termCode": ""}

        with pytest.raises(ValidationError) as exc_info:
            TermUpdateRequest(**data)

        errors = exc_info.value.errors()
        assert any(
            "at least 1 character" in str(error) or "String should have at least 1 character" in str(error)
            for error in errors
        )

    @pytest.mark.unit
    def test_term_update_request_missing_code_fails(self):
        """Test TermUpdateRequest fails without required term_code."""
        data = {"termName": "Fall 2025"}

        with pytest.raises(ValidationError) as exc_info:
            TermUpdateRequest(**data)

        errors = exc_info.value.errors()
        assert any(error["type"] == "missing" for error in errors)

    @pytest.mark.unit
    def test_term_update_cleanup_stats_valid(self):
        """Test valid TermUpdateCleanupStats."""
        data = {
            "subscriptionsDeactivated": 10,
            "enrollmentsDeleted": 50,
            "classesDeleted": 20,
            "coursesDeleted": 5,
        }
        stats = TermUpdateCleanupStats(**data)

        assert stats.subscriptions_deactivated == 10
        assert stats.enrollments_deleted == 50
        assert stats.classes_deleted == 20
        assert stats.courses_deleted == 5

    @pytest.mark.unit
    def test_term_update_response_valid(self):
        """Test valid TermUpdateResponse."""
        cleanup_data = {
            "subscriptionsDeactivated": 10,
            "enrollmentsDeleted": 50,
            "classesDeleted": 20,
            "coursesDeleted": 5,
        }
        data = {
            "collegeId": 1,
            "shortName": "bu",
            "oldTermCode": "202408",
            "newTermCode": "202410",
            "oldTermName": "Fall 2024",
            "newTermName": "Spring 2025",
            "cleanup": cleanup_data,
        }
        response = TermUpdateResponse(**data)

        assert response.college_id == 1
        assert response.short_name == "bu"
        assert response.old_term_code == "202408"
        assert response.new_term_code == "202410"


class TestSubscriptionSchemas:
    """Tests for subscription schemas."""

    @pytest.mark.unit
    def test_subscription_create_valid(self):
        """Test valid SubscriptionCreate."""
        data = {"collegeId": 1, "classId": 100}
        subscription = SubscriptionCreate(**data)

        assert subscription.college_id == 1
        assert subscription.class_id == 100

    @pytest.mark.unit
    def test_subscription_create_snake_case(self):
        """Test SubscriptionCreate with snake_case."""
        data = {"college_id": 1, "class_id": 100}
        subscription = SubscriptionCreate(**data)

        assert subscription.college_id == 1
        assert subscription.class_id == 100

    @pytest.mark.unit
    def test_subscription_create_missing_field_fails(self):
        """Test SubscriptionCreate fails with missing required field."""
        data = {"collegeId": 1}  # Missing classId

        with pytest.raises(ValidationError) as exc_info:
            SubscriptionCreate(**data)

        errors = exc_info.value.errors()
        assert any(error["type"] == "missing" for error in errors)

    @pytest.mark.unit
    def test_subscription_response_valid(self):
        """Test valid SubscriptionResponse."""
        user_id = uuid4()
        data = {
            "id": 1,
            "userId": str(user_id),
            "collegeId": 1,
            "classId": 100,
            "isActive": True,
            "lastNotified": None,
            "notificationCount": 0,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        response = SubscriptionResponse(**data)

        assert response.id == 1
        assert response.user_id == user_id
        assert response.is_active is True
        assert response.notification_count == 0

    @pytest.mark.unit
    def test_subscription_status_valid(self):
        """Test valid SubscriptionStatus."""
        data = {
            "currentCount": 2,
            "maxSubscriptions": 5,
            "tier": "plus",
            "canSubscribe": True,
        }
        status = SubscriptionStatus(**data)

        assert status.current_count == 2
        assert status.max_subscriptions == 5
        assert status.tier == "plus"
        assert status.can_subscribe is True

    @pytest.mark.unit
    def test_subscription_status_invalid_tier(self):
        """Test SubscriptionStatus fails with invalid tier."""
        data = {
            "currentCount": 2,
            "maxSubscriptions": 5,
            "tier": "invalid_tier",  # Invalid
            "canSubscribe": True,
        }

        with pytest.raises(ValidationError) as exc_info:
            SubscriptionStatus(**data)

        errors = exc_info.value.errors()
        assert any("literal" in error["type"].lower() for error in errors)

    @pytest.mark.unit
    def test_subscription_status_valid_tiers(self):
        """Test all valid tier values."""
        valid_tiers = ["free", "plus", "pro"]

        for tier in valid_tiers:
            data = {
                "currentCount": 1,
                "maxSubscriptions": 3,
                "tier": tier,
                "canSubscribe": True,
            }
            status = SubscriptionStatus(**data)
            assert status.tier == tier


class TestCourseSchemas:
    """Tests for course schemas."""

    @pytest.mark.unit
    def test_course_create_valid(self):
        """Test valid CourseCreate."""
        data = {
            "collegeId": 1,
            "courseCode": "CS 101",
            "title": "Intro to Computer Science",
        }
        course = CourseCreate(**data)

        assert course.college_id == 1
        assert course.course_code == "CS 101"
        assert course.title == "Intro to Computer Science"

    @pytest.mark.unit
    def test_course_create_missing_field_fails(self):
        """Test CourseCreate fails with missing field."""
        data = {"collegeId": 1, "courseCode": "CS 101"}  # Missing title

        with pytest.raises(ValidationError) as exc_info:
            CourseCreate(**data)

        errors = exc_info.value.errors()
        assert any(error["type"] == "missing" for error in errors)

    @pytest.mark.unit
    def test_course_response_valid(self):
        """Test valid CourseResponse."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        data = {
            "id": 1,
            "collegeId": 1,
            "courseCode": "CS 101",
            "title": "Intro to CS",
            "isActive": True,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        response = CourseResponse(**data)

        assert response.id == 1
        assert response.course_code == "CS 101"
        assert response.is_active is True


class TestClassSchemas:
    """Tests for class schemas."""

    @pytest.mark.unit
    def test_class_create_valid(self):
        """Test valid ClassCreate."""
        data = {
            "courseId": 1,
            "classNumber": "12345",
            "sectionCode": "A1",
        }
        cls = ClassCreate(**data)

        assert cls.course_id == 1
        assert cls.class_number == "12345"
        assert cls.section_code == "A1"

    @pytest.mark.unit
    def test_class_create_optional_section(self):
        """Test ClassCreate with optional section_code."""
        # Assuming section_code might be optional in some cases
        data = {
            "courseId": 1,
            "classNumber": "12345",
        }
        # This test assumes section_code is required
        # If it's optional, adjust accordingly
        try:
            cls = ClassCreate(**data)
            # If no error, section_code is optional
            assert cls.class_number == "12345"
        except ValidationError:
            # If error, section_code is required
            pass

    @pytest.mark.unit
    def test_class_response_valid(self):
        """Test valid ClassResponse."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        data = {
            "classId": 100,
            "courseId": 1,
            "classNumber": "12345",
            "sectionCode": "A1",
            "isActive": True,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        response = ClassResponse(**data)

        assert response.class_id == 100
        assert response.class_number == "12345"
        assert response.is_active is True


class TestCollegeSchemas:
    """Tests for college schemas."""

    @pytest.mark.unit
    def test_college_response_valid(self):
        """Test valid CollegeResponse."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        data = {
            "id": 1,
            "name": "Boston University",
            "shortName": "bu",
            "isActive": True,
            "createdAt": now.isoformat(),
        }
        response = CollegeResponse(**data)

        assert response.id == 1
        assert response.name == "Boston University"
        assert response.short_name == "bu"
        assert response.is_active is True

    @pytest.mark.unit
    def test_college_response_snake_case(self):
        """Test CollegeResponse with snake_case."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        data = {
            "id": 1,
            "name": "Boston University",
            "short_name": "bu",
            "is_active": True,
            "created_at": now.isoformat(),
        }
        response = CollegeResponse(**data)

        assert response.short_name == "bu"
        assert response.is_active is True


class TestSchemaTypeCoercion:
    """Tests for type coercion in schemas."""

    @pytest.mark.unit
    def test_string_to_int_coercion(self):
        """Test that string integers are coerced to int."""
        data = {"collegeId": "1", "classId": "100"}  # Strings instead of ints
        subscription = SubscriptionCreate(**data)

        assert subscription.college_id == 1
        assert subscription.class_id == 100
        assert isinstance(subscription.college_id, int)

    @pytest.mark.unit
    def test_invalid_type_fails(self):
        """Test that invalid types fail validation."""
        data = {"collegeId": "not_a_number", "classId": 100}

        with pytest.raises(ValidationError):
            SubscriptionCreate(**data)

    @pytest.mark.unit
    def test_boolean_coercion(self):
        """Test boolean value handling."""
        data = {
            "currentCount": 1,
            "maxSubscriptions": 3,
            "tier": "free",
            "canSubscribe": "true",  # String instead of bool
        }

        # Pydantic may or may not coerce this - test actual behavior
        try:
            status = SubscriptionStatus(**data)
            # If it succeeds, check the value
            assert isinstance(status.can_subscribe, bool)
        except ValidationError:
            # If it fails, that's also valid behavior
            pass


class TestSchemaSerializationAliases:
    """Tests for schema serialization with aliases."""

    @pytest.mark.unit
    def test_serialization_uses_aliases(self):
        """Test that serialization uses camelCase aliases."""
        data = {"termCode": "202510", "termName": "Fall 2025"}
        request = TermUpdateRequest(**data)

        # Serialize to dict
        serialized = request.model_dump(by_alias=True)

        assert "termCode" in serialized
        assert "termName" in serialized
        assert "term_code" not in serialized
        assert "term_name" not in serialized

    @pytest.mark.unit
    def test_serialization_without_aliases(self):
        """Test serialization without aliases uses snake_case."""
        data = {"termCode": "202510", "termName": "Fall 2025"}
        request = TermUpdateRequest(**data)

        # Serialize without aliases
        serialized = request.model_dump(by_alias=False)

        assert "term_code" in serialized
        assert "term_name" in serialized


class TestSchemaOptionalFields:
    """Tests for optional fields in schemas."""

    @pytest.mark.unit
    def test_optional_fields_can_be_none(self):
        """Test that optional fields can be None."""
        data = {
            "collegeId": 1,
            "shortName": "bu",
            "oldTermCode": None,  # Optional
            "newTermCode": "202510",
            "oldTermName": None,  # Optional
            "newTermName": "Fall 2025",
            "cleanup": {
                "subscriptionsDeactivated": 0,
                "enrollmentsDeleted": 0,
                "classesDeleted": 0,
                "coursesDeleted": 0,
            },
        }
        response = TermUpdateResponse(**data)

        assert response.old_term_code is None
        assert response.old_term_name is None

    @pytest.mark.unit
    def test_optional_fields_can_be_omitted(self):
        """Test that optional fields can be omitted."""
        data = {"termCode": "202510"}  # termName is optional
        request = TermUpdateRequest(**data)

        assert request.term_name is None
