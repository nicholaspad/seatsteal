"""Tests for root API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Tests for GET /health endpoint."""

    @pytest.mark.unit
    async def test_health_check_success(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "seatsteal-api"
        assert "version" in data
        assert "environment" in data


class TestRoot:
    """Tests for GET / endpoint."""

    @pytest.mark.unit
    async def test_root_success(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "SeatSteal" in data["message"]
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
