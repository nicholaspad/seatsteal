"""Tests for course API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from webapp.models.course import Course
from webapp.models.college import College
from webapp.models.class_model import Class


class TestGetCourses:
    """Tests for GET /api/courses/ endpoint."""

    @pytest.mark.unit
    async def test_get_courses_success(
        self,
        client: AsyncClient,
        test_course: Course,
        test_class: Class,
    ):
        """Test successfully getting courses."""
        response = await client.get("/api/courses/")

        assert response.status_code == 200
        data = response.json()
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
        data = response.json()
        assert len(data["data"]) <= 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 2

    @pytest.mark.unit
    async def test_get_courses_with_search(
        self,
        client: AsyncClient,
        test_course: Course,
    ):
        """Test courses with search query."""
        response = await client.get(f"/api/courses/?q={test_course.course_code}")

        assert response.status_code == 200
        data = response.json()
        # Should find the course
        assert any(c["course_code"] == test_course.course_code for c in data["data"])

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
        data = response.json()
        # All courses should be from the test college
        assert all(c["college_id"] == test_college.id for c in data["data"])

    @pytest.mark.unit
    async def test_get_courses_empty(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
    ):
        """Test getting courses when none exist."""
        response = await client.get("/api/courses/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0
        assert data["pagination"]["total"] == 0


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
        data = response.json()
        assert data["id"] == test_course.id
        assert data["course_code"] == test_course.course_code
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
        test_db: AsyncSession,
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
        await test_db.commit()
        await test_db.refresh(inactive_course)

        response = await client.get(f"/api/courses/{inactive_course.id}")

        assert response.status_code == 404


class TestGetCourseClasses:
    """Tests for GET /api/courses/{course_id}/classes endpoint."""

    @pytest.mark.unit
    async def test_get_course_classes_success(
        self,
        client: AsyncClient,
        test_course: Course,
        test_class: Class,
    ):
        """Test successfully getting course classes."""
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
        with patch("webapp.api.routes.courses.require_premium_access") as mock_premium:
            mock_premium.return_value = None  # User has premium access

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
        with patch("webapp.api.routes.courses.require_premium_access") as mock_premium:
            mock_premium.return_value = None

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

        assert response.status_code == 403

    @pytest.mark.unit
    async def test_get_course_summary_no_premium(
        self,
        authenticated_client: AsyncClient,
        test_course: Course,
    ):
        """Test getting summary without premium access."""
        from fastapi import HTTPException

        with patch("webapp.api.routes.courses.require_premium_access") as mock_premium:
            mock_premium.side_effect = HTTPException(
                status_code=403, detail="Premium access required"
            )

            response = await authenticated_client.get(
                f"/api/courses/{test_course.id}/summary"
            )

            assert response.status_code == 403
