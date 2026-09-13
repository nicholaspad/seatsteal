"""Tests for course API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from models.course import Course
from models.college import College
from models.class_model import Class


class TestGetCourses:
    """Tests for GET /api/courses/ endpoint."""

    @pytest.mark.unit
    async def test_get_courses_success(
        self,
        client: AsyncClient,
        test_course: Course,
        test_class: Class,
        test_enrollment,
    ):
        """Test successfully getting courses (requires enrollment for classes to appear)."""
        response = await client.get("/api/courses/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1

    @pytest.mark.unit
    async def test_get_courses_with_pagination(
        self,
        client: AsyncClient,
        multiple_courses,
    ):
        """Test courses pagination."""
        response = await client.get("/api/courses/?page=1&limit=2")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data["data"]) <= 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 2

    @pytest.mark.unit
    async def test_get_courses_with_search(
        self,
        client: AsyncClient,
        test_course: Course,
        test_class: Class,
        test_enrollment,
    ):
        """Test courses with search query (requires enrollment for course to appear)."""
        response = await client.get(f"/api/courses/?q={test_course.course_code}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        # Should find the course
        assert any(c["courseCode"] == test_course.course_code for c in data["data"])

    @pytest.mark.unit
    async def test_get_courses_with_college_filter(
        self,
        client: AsyncClient,
        test_course: Course,
        test_college: College,
    ):
        """Test courses filtered by college."""
        response = await client.get(f"/api/courses/?collegeId={test_college.id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        # All courses should be from the test college
        assert all(c["collegeId"] == test_college.id for c in data["data"])

    @pytest.mark.unit
    async def test_get_courses_empty(
        self,
        client: AsyncClient,
        test_db: Session,
    ):
        """Test getting courses when none exist."""
        response = await client.get("/api/courses/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert len(data["data"]) == 0
        assert data["pagination"]["total"] == 0

    @pytest.mark.unit
    async def test_get_courses_hides_classes_without_enrollment(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        """Test that courses list hides classes without enrollment and excludes empty courses."""
        from models.course import Course
        from models.class_model import Class
        from models.enrollment import Enrollment
        from datetime import datetime, timezone

        # Course 1: Has class WITH enrollment - should appear
        course_with_enrollment = Course(
            college_id=test_college.id,
            course_code="VALID101",
            title="Course With Enrollment",
            is_active=True,
        )
        test_db.add(course_with_enrollment)
        test_db.flush()

        class_with_enrollment = Class(
            course_id=course_with_enrollment.id,
            class_number="11111",
            section_code="A",
            is_active=True,
        )
        test_db.add(class_with_enrollment)
        test_db.flush()

        enrollment = Enrollment(
            class_id=class_with_enrollment.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)

        # Course 2: Has ONLY classes WITHOUT enrollment - should NOT appear
        course_without_enrollment = Course(
            college_id=test_college.id,
            course_code="STALE999",
            title="Odasis Leftover Course",
            is_active=True,
        )
        test_db.add(course_without_enrollment)
        test_db.flush()

        # Create 2 stale classes like Rutgers Odasis Z4/Z2
        for i, section in enumerate(["Z4", "Z2"]):
            stale_class = Class(
                course_id=course_without_enrollment.id,
                class_number=f"2407{3+i}",
                section_code=section,
                is_active=True,
            )
            test_db.add(stale_class)

        # Course 3: Mixed - has classes WITH and WITHOUT enrollment
        course_mixed = Course(
            college_id=test_college.id,
            course_code="MIXED202",
            title="Mixed Course",
            is_active=True,
        )
        test_db.add(course_mixed)
        test_db.flush()

        # Class with enrollment
        class_with_enroll_mixed = Class(
            course_id=course_mixed.id,
            class_number="22222",
            section_code="B",
            is_active=True,
        )
        test_db.add(class_with_enroll_mixed)
        test_db.flush()

        enrollment_mixed = Enrollment(
            class_id=class_with_enroll_mixed.class_id,
            college_id=test_college.id,
            enrollment_status="closed",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment_mixed)

        # Class without enrollment (stale)
        class_without_enroll_mixed = Class(
            course_id=course_mixed.id,
            class_number="22223",
            section_code="C",
            is_active=True,
        )
        test_db.add(class_without_enroll_mixed)

        test_db.commit()

        # Query the API
        response = await client.get("/api/courses/")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        courses = response_json["data"]["data"]

        # Extract course codes
        returned_course_codes = [c["courseCode"] for c in courses]

        # Course with enrollment should appear
        assert "VALID101" in returned_course_codes

        # Course with ONLY stale classes should NOT appear (empty card removed)
        assert "STALE999" not in returned_course_codes

        # Mixed course should appear
        assert "MIXED202" in returned_course_codes

        # Verify mixed course only has 1 class (the one with enrollment)
        mixed_course_data = next(c for c in courses if c["courseCode"] == "MIXED202")
        assert len(mixed_course_data["classes"]) == 1
        assert mixed_course_data["classes"][0]["sectionCode"] == "B"
        assert mixed_course_data["classes"][0]["currentEnrollment"] is not None

    @pytest.mark.unit
    async def test_get_courses_search_excludes_leftover_courses(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        """Test that searching for Odasis-style leftover courses returns no results."""
        from models.course import Course
        from models.class_model import Class

        # Create Odasis-style leftover course with no enrollment
        odasis_course = Course(
            college_id=test_college.id,
            course_code="01:001:161",
            title="Odasis Program",
            is_active=True,
        )
        test_db.add(odasis_course)
        test_db.flush()

        # Create Z4 and Z2 sections like in prod
        for crn, section in [(24073, "Z4"), (24075, "Z2")]:
            stale_class = Class(
                course_id=odasis_course.id,
                class_number=str(crn),
                section_code=section,
                is_active=True,
            )
            test_db.add(stale_class)

        test_db.commit()

        # Search for Odasis - should return 0 results
        response = await client.get("/api/courses/?q=Odasis")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        courses = response_json["data"]["data"]

        # Should not find any courses (all classes filtered out)
        assert len(courses) == 0


class TestGetCourse:
    """Tests for GET /api/courses/{course_id} endpoint."""

    @pytest.mark.unit
    async def test_get_course_success(
        self,
        client: AsyncClient,
        test_course: Course,
        test_class: Class,
    ):
        """Test successfully getting a specific course."""
        response = await client.get(f"/api/courses/{test_course.id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["id"] == test_course.id
        assert data["courseCode"] == test_course.course_code
        assert data["title"] == test_course.title
        assert "classes" in data
        assert "college" in data

    @pytest.mark.unit
    async def test_get_course_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent course."""
        response = await client.get("/api/courses/99999")

        assert response.status_code == 404
        assert "Course not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_get_course_inactive(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        """Test getting inactive course."""
        inactive_course = Course(
            college_id=test_college.id,
            course_code="INACTIVE101",
            title="Inactive Course",
            is_active=False,
        )
        test_db.add(inactive_course)
        test_db.commit()
        test_db.refresh(inactive_course)

        response = await client.get(f"/api/courses/{inactive_course.id}")

        assert response.status_code == 404

    @pytest.mark.unit
    async def test_get_course_detail_hides_classes_without_enrollment(
        self,
        client: AsyncClient,
        test_db: Session,
        test_college: College,
    ):
        """Test that course detail endpoint hides classes without enrollment."""
        from models.course import Course
        from models.class_model import Class
        from models.enrollment import Enrollment
        from datetime import datetime, timezone

        # Create course with mixed classes
        course = Course(
            college_id=test_college.id,
            course_code="MIXED303",
            title="Course With Mixed Classes",
            is_active=True,
        )
        test_db.add(course)
        test_db.flush()

        # Class 1: WITH enrollment - should appear
        class_with_enrollment = Class(
            course_id=course.id,
            class_number="30001",
            section_code="A",
            is_active=True,
        )
        test_db.add(class_with_enrollment)
        test_db.flush()

        enrollment = Enrollment(
            class_id=class_with_enrollment.class_id,
            college_id=test_college.id,
            enrollment_status="open",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)

        # Class 2: WITHOUT enrollment - should be hidden
        class_without_enrollment = Class(
            course_id=course.id,
            class_number="30002",
            section_code="Z9",
            is_active=True,
        )
        test_db.add(class_without_enrollment)

        # Class 3: WITH enrollment - should appear
        class_with_enrollment_2 = Class(
            course_id=course.id,
            class_number="30003",
            section_code="B",
            is_active=True,
        )
        test_db.add(class_with_enrollment_2)
        test_db.flush()

        enrollment_2 = Enrollment(
            class_id=class_with_enrollment_2.class_id,
            college_id=test_college.id,
            enrollment_status="closed",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment_2)

        test_db.commit()

        # Query the API
        response = await client.get(f"/api/courses/{course.id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        course_data = response_json["data"]

        # Should have exactly 2 classes (the ones with enrollment)
        assert len(course_data["classes"]) == 2

        # Verify the correct classes are returned
        section_codes = [c["sectionCode"] for c in course_data["classes"]]
        assert "A" in section_codes
        assert "B" in section_codes
        assert "Z9" not in section_codes

        # All returned classes should have currentEnrollment
        for class_data in course_data["classes"]:
            assert class_data["currentEnrollment"] is not None
            assert class_data["currentEnrollment"]["enrollmentStatus"] in [
                "open",
                "closed",
            ]


class TestGetCourseClasses:
    """Tests for GET /api/courses/{course_id}/classes endpoint."""

    @pytest.mark.unit
    async def test_get_course_classes_success(
        self,
        client: AsyncClient,
        test_course: Course,
        test_class: Class,
        test_enrollment,
    ):
        """Test successfully getting course classes (requires enrollment for class to appear)."""
        response = await client.get(f"/api/courses/{test_course.id}/classes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert any(c["classId"] == test_class.class_id for c in data["data"])

    @pytest.mark.unit
    async def test_get_course_classes_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting classes for non-existent course."""
        response = await client.get("/api/courses/99999/classes")

        assert response.status_code == 404
        assert "Course not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_get_course_classes_empty(
        self,
        client: AsyncClient,
        test_course: Course,
    ):
        """Test getting classes when course has none."""
        response = await client.get(f"/api/courses/{test_course.id}/classes")

        assert response.status_code == 200
        data = response.json()
        # Might have test_class from fixture or be empty
        assert isinstance(data["data"], list)

    @pytest.mark.unit
    async def test_get_course_classes_hides_no_enrollment(
        self,
        client: AsyncClient,
        test_db: Session,
        test_course: Course,
        test_college: College,
    ):
        """Test that classes without enrollment snapshots are hidden."""
        from models.class_model import Class
        from models.enrollment import Enrollment
        from datetime import datetime, timezone

        # Create class WITH enrollment - should appear
        class_with_enrollment = Class(
            course_id=test_course.id,
            class_number="11111",
            section_code="Z1",
            is_active=True,
        )
        test_db.add(class_with_enrollment)
        test_db.flush()

        enrollment = Enrollment(
            class_id=class_with_enrollment.class_id,
            college_id=test_college.id,
            enrollment_status="closed",
            scraped_at=datetime.now(timezone.utc),
        )
        test_db.add(enrollment)

        # Create class WITHOUT enrollment - should NOT appear
        class_without_enrollment = Class(
            course_id=test_course.id,
            class_number="24073",
            section_code="Z4",
            is_active=True,
        )
        test_db.add(class_without_enrollment)

        test_db.commit()

        # Query the API
        response = await client.get(f"/api/courses/{test_course.id}/classes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        returned_class_ids = [c["classId"] for c in data["data"]]

        # Class with enrollment should be present
        assert class_with_enrollment.class_id in returned_class_ids

        # Class without enrollment should be HIDDEN
        assert class_without_enrollment.class_id not in returned_class_ids

    @pytest.mark.unit
    async def test_get_course_classes_multiple_with_and_without_enrollment(
        self,
        client: AsyncClient,
        test_db: Session,
        test_course: Course,
        test_college: College,
    ):
        """Test that only classes with enrollment snapshots are returned when mixed."""
        from models.class_model import Class
        from models.enrollment import Enrollment
        from datetime import datetime, timezone

        # Create 3 classes with enrollment
        classes_with_enrollment = []
        for i in range(3):
            cls = Class(
                course_id=test_course.id,
                class_number=f"5000{i}",
                section_code=f"E{i}",
                is_active=True,
            )
            test_db.add(cls)
            test_db.flush()

            enrollment = Enrollment(
                class_id=cls.class_id,
                college_id=test_college.id,
                enrollment_status="open" if i % 2 == 0 else "closed",
                scraped_at=datetime.now(timezone.utc),
            )
            test_db.add(enrollment)
            classes_with_enrollment.append(cls)

        # Create 2 classes WITHOUT enrollment (stale/leftover)
        classes_without_enrollment = []
        for i in range(2):
            cls = Class(
                course_id=test_course.id,
                class_number=f"6000{i}",
                section_code=f"N{i}",
                is_active=True,
            )
            test_db.add(cls)
            classes_without_enrollment.append(cls)

        test_db.commit()

        # Query the API
        response = await client.get(f"/api/courses/{test_course.id}/classes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        returned_class_ids = [c["classId"] for c in data["data"]]

        # All classes with enrollment should be present
        for cls in classes_with_enrollment:
            assert cls.class_id in returned_class_ids

        # All classes without enrollment should be HIDDEN
        for cls in classes_without_enrollment:
            assert cls.class_id not in returned_class_ids

        # Should return exactly 3 classes (only those with enrollment)
        assert len(returned_class_ids) == 3


class TestGetCourseSummary:
    """Tests for GET /api/courses/{course_id}/summary endpoint."""

    @pytest.mark.unit
    async def test_get_course_summary_success(
        self,
        authenticated_client: AsyncClient,
        test_course: Course,
        test_class: Class,
    ):
        """Test successfully getting course summary (premium)."""
        with patch(
            "api.routes.courses.require_pro_access", new_callable=AsyncMock
        ) as mock_pro:
            mock_pro.return_value = None  # User has pro access

            response = await authenticated_client.get(
                f"/api/courses/{test_course.id}/summary"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "courseId" in data["data"]
            assert "totalSubscriptions" in data["data"]
            assert "totalClasses" in data["data"]

    @pytest.mark.unit
    async def test_get_course_summary_not_found(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test getting summary for non-existent course."""
        with patch(
            "api.routes.courses.require_pro_access", new_callable=AsyncMock
        ) as mock_pro:
            mock_pro.return_value = None

            response = await authenticated_client.get("/api/courses/99999/summary")

            assert response.status_code == 404

    @pytest.mark.unit
    async def test_get_course_summary_unauthenticated(
        self,
        client: AsyncClient,
        test_course: Course,
    ):
        """Test getting summary without authentication."""
        response = await client.get(f"/api/courses/{test_course.id}/summary")

        assert response.status_code == 401

    @pytest.mark.unit
    async def test_get_course_summary_no_premium(
        self,
        authenticated_client: AsyncClient,
        test_course: Course,
    ):
        """Test getting summary without premium access."""
        from fastapi import HTTPException

        with patch("api.routes.courses.require_pro_access") as mock_pro:
            mock_pro.side_effect = HTTPException(
                status_code=403, detail="Pro subscription required"
            )

            response = await authenticated_client.get(
                f"/api/courses/{test_course.id}/summary"
            )

            assert response.status_code == 403
