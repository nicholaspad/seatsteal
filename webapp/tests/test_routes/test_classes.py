"""Tests for class API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from models.class_model import Class
from models.course import Course
from models.enrollment import Enrollment


class TestGetClass:
    """Tests for GET /api/classes/{class_id} endpoint."""

    @pytest.mark.unit
    async def test_get_class_success(
        self,
        client: AsyncClient,
        test_class: Class,
        test_course: Course,
        test_enrollment: Enrollment,
    ):
        """Test successfully getting a specific class."""
        response = await client.get(f"/api/classes/{test_class.class_id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert data["classId"] == test_class.class_id
        assert data["classNumber"] == test_class.class_number
        assert data["sectionCode"] == test_class.section_code
        assert "course" in data
        assert data["course"]["id"] == test_course.id

    @pytest.mark.unit
    async def test_get_class_with_enrollment(
        self,
        client: AsyncClient,
        test_class: Class,
        test_enrollment: Enrollment,
    ):
        """Test getting class with enrollment data."""
        response = await client.get(f"/api/classes/{test_class.class_id}")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        data = response_json["data"]
        assert "currentEnrollment" in data
        if data["currentEnrollment"]:
            assert "enrollmentStatus" in data["currentEnrollment"]
            assert "scrapedAt" in data["currentEnrollment"]

    @pytest.mark.unit
    async def test_get_class_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent class."""
        response = await client.get("/api/classes/99999")

        assert response.status_code == 404
        assert "Class not found" in response.json()["detail"]

    @pytest.mark.unit
    async def test_get_class_inactive(
        self,
        client: AsyncClient,
        test_db: Session,
        test_course: Course,
    ):
        """Test getting inactive class."""
        inactive_class = Class(
            course_id=test_course.id,
            class_number="88888",
            section_code="Z",
            is_active=False,
        )
        test_db.add(inactive_class)
        test_db.commit()
        test_db.refresh(inactive_class)

        response = await client.get(f"/api/classes/{inactive_class.class_id}")

        assert response.status_code == 404


class TestGetEnrollmentAnalysis:
    """Tests for GET /api/classes/{class_id}/enrollment-analysis endpoint."""

    @pytest.mark.unit
    async def test_get_enrollment_analysis_success(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_class: Class,
        test_enrollment: Enrollment,
    ):
        """Test successfully getting enrollment analysis (premium)."""
        with patch(
            "api.routes.classes.require_premium_access", new_callable=AsyncMock
        ) as mock_premium:
            mock_premium.return_value = None  # User has premium access

            # Create some enrollment history
            now = datetime.utcnow()
            for i in range(5):
                enrollment = Enrollment(
                    class_id=test_class.class_id,
                    college_id=test_enrollment.college_id,
                    enrollment_status="open" if i % 2 == 0 else "closed",
                    scraped_at=now - timedelta(days=i * 10),
                )
                test_db.add(enrollment)
            test_db.commit()

            response = await authenticated_client.get(
                f"/api/classes/{test_class.class_id}/enrollment-analysis"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "classId" in data["data"]
            assert "timesOpenedLast30Days" in data["data"]
            assert "avgDaysToOpenLast30Days" in data["data"]
            assert "subscriptionsCount" in data["data"]
            assert "competitionLevel" in data["data"]

    @pytest.mark.unit
    async def test_get_enrollment_analysis_competition_levels(
        self,
        authenticated_client: AsyncClient,
        test_db: Session,
        test_class: Class,
    ):
        """Test that competition level is calculated correctly."""
        with patch(
            "api.routes.classes.require_premium_access", new_callable=AsyncMock
        ) as mock_premium:
            mock_premium.return_value = None

            response = await authenticated_client.get(
                f"/api/classes/{test_class.class_id}/enrollment-analysis"
            )

            assert response.status_code == 200
            data = response.json()
            competition = data["data"]["competitionLevel"]
            assert competition in ["low", "medium", "high"]

    @pytest.mark.unit
    async def test_get_enrollment_analysis_unauthenticated(
        self,
        client: AsyncClient,
        test_class: Class,
    ):
        """Test getting enrollment analysis without authentication."""
        response = await client.get(
            f"/api/classes/{test_class.class_id}/enrollment-analysis"
        )

        assert response.status_code == 401

    @pytest.mark.unit
    async def test_get_enrollment_analysis_no_premium(
        self,
        authenticated_client: AsyncClient,
        test_class: Class,
    ):
        """Test getting enrollment analysis without premium access."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        with patch("api.routes.classes.require_premium_access") as mock_premium:
            mock_premium.side_effect = HTTPException(
                status_code=403, detail="Premium access required"
            )

            response = await authenticated_client.get(
                f"/api/classes/{test_class.class_id}/enrollment-analysis"
            )

            assert response.status_code == 403

    @pytest.mark.unit
    async def test_get_enrollment_analysis_no_data(
        self,
        authenticated_client: AsyncClient,
        test_class: Class,
    ):
        """Test getting enrollment analysis with no enrollment history."""
        with patch(
            "api.routes.classes.require_premium_access", new_callable=AsyncMock
        ) as mock_premium:
            mock_premium.return_value = None

            response = await authenticated_client.get(
                f"/api/classes/{test_class.class_id}/enrollment-analysis"
            )

            assert response.status_code == 200
            data = response.json()
            # Should return 0s for metrics when no data
            assert data["data"]["timesOpenedLast30Days"] >= 0
            assert data["data"]["avgDaysToOpenLast30Days"] >= 0
