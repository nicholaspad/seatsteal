"""Tests for term codes API routes."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
import json
import base64

from api.routes.term_codes import (
    fetch_brown_terms,
    fetch_bu_terms,
    fetch_cornell_terms,
    fetch_neu_terms,
    fetch_usc_terms,
    fetch_umd_terms,
    fetch_rutgers_terms,
    fetch_upenn_terms,
    fetch_uf_terms,
)


class TestFetchBrownTerms:
    """Tests for fetch_brown_terms function."""

    @pytest.mark.unit
    async def test_fetch_brown_success(self):
        """Test successful fetching of Brown terms."""
        mock_html = """
        <select>
            <option value="202410">Fall 2024</option>
            <option value="202420">Spring 2025</option>
            <option value="Any Term">Any Term</option>
            <option value="202430">Summer 2025</option>
        </select>
        """

        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_brown_terms()

            assert status == "success"
            assert len(terms) <= 4
            assert error is None
            assert any(term["code"] == "202410" for term in terms)
            assert all("Any Term" not in term["description"] for term in terms)

    @pytest.mark.unit
    async def test_fetch_brown_network_error(self):
        """Test Brown terms fetch with network error."""
        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            status, terms, error = await fetch_brown_terms()

            assert status == "error"
            assert terms == []
            assert error is not None
            assert "Network error" in error


class TestFetchBUTerms:
    """Tests for fetch_bu_terms function."""

    @pytest.mark.unit
    async def test_fetch_bu_success(self):
        """Test successful fetching of BU terms."""
        search_options = {
            "search_options": {
                "terms": [
                    {"strm": "2248", "descr": "Fall 2024"},
                    {"strm": "2252", "descr": "Spring 2025"},
                    {"strm": "2254", "descr": "Summer 2025"},
                ]
            }
        }
        json_str = json.dumps(search_options)
        b64_data = base64.b64encode(json_str.encode()).decode()

        mock_html = f"atob(`{b64_data}`)"
        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_bu_terms()

            assert status == "success"
            assert len(terms) == 3
            assert error is None
            assert terms[0]["code"] == "2248"
            assert terms[0]["description"] == "Fall 2024"

    @pytest.mark.unit
    async def test_fetch_bu_no_base64_data(self):
        """Test BU terms fetch when base64 data not found."""
        mock_response = MagicMock()
        mock_response.text = "<html>No atob data here</html>"

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_bu_terms()

            assert status == "error"
            assert terms == []
            assert error == "Could not find base64 data"

    @pytest.mark.unit
    async def test_fetch_bu_invalid_json(self):
        """Test BU terms fetch with invalid JSON in base64."""
        invalid_json = "not valid json"
        b64_data = base64.b64encode(invalid_json.encode()).decode()
        mock_html = f"atob(`{b64_data}`)"
        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_bu_terms()

            assert status == "error"
            assert terms == []
            assert error is not None


class TestFetchCornellTerms:
    """Tests for fetch_cornell_terms function."""

    @pytest.mark.unit
    async def test_fetch_cornell_success(self):
        """Test successful fetching of Cornell terms."""
        mock_html = """
        <a href="/browse/roster/SP26">Spring 2026</a>
        <a href="/browse/roster/FA25">Fall 2025</a>
        <a href="/browse/roster/SP25">Spring 2025</a>
        <a href="/clear">Clear Roster</a>
        """

        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_cornell_terms()

            assert status == "success"
            assert len(terms) <= 4
            assert error is None
            assert any(term["code"] == "SP26" for term in terms)
            assert all("clear" not in term["description"].lower() for term in terms)
            assert all("Roster" not in term["description"] for term in terms)


class TestFetchNEUTerms:
    """Tests for fetch_neu_terms function."""

    @pytest.mark.unit
    async def test_fetch_neu_success(self):
        """Test successful fetching of NEU terms."""
        mock_json = [
            {"code": "202510", "description": "Fall 2024"},
            {"code": "202530", "description": "Spring 2025"},
            {"code": "202540", "description": "Summer 2025"},
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_json

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_neu_terms()

            assert status == "success"
            assert len(terms) == 3
            assert error is None
            assert terms[0]["code"] == "202510"


class TestFetchUSCTerms:
    """Tests for fetch_usc_terms function."""

    @pytest.mark.unit
    async def test_fetch_usc_success(self):
        """Test successful fetching of USC terms."""
        mock_json = [
            {
                "termCode": "20243",
                "season": "Fall",
                "year": 2024,
                "status": "Registration",
            },
            {
                "termCode": "20251",
                "season": "Spring",
                "year": 2025,
                "status": "Open",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_json

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_usc_terms()

            assert status == "success"
            assert len(terms) == 2
            assert error is None
            assert terms[0]["code"] == "20243"
            assert "Fall 2024" in terms[0]["description"]
            assert "Registration" in terms[0]["description"]


class TestFetchUMDTerms:
    """Tests for fetch_umd_terms function."""

    @pytest.mark.unit
    async def test_fetch_umd_success(self):
        """Test successful fetching of UMD terms."""
        mock_html = """
        <select>
            <option value="202408">Fall 2024</option>
            <option value="202501">Spring 2025</option>
            <option value="202505">Summer 2025</option>
            <option value="123">Invalid</option>
        </select>
        """

        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_umd_terms()

            assert status == "success"
            assert len(terms) <= 4
            assert error is None
            # Should only include 6-digit codes
            assert all(len(term["code"]) == 6 for term in terms)
            assert any(term["code"] == "202408" for term in terms)


class TestFetchRutgersTerms:
    """Tests for fetch_rutgers_terms function."""

    @pytest.mark.unit
    async def test_fetch_rutgers_success(self):
        """Test successful fetching of Rutgers terms."""
        mock_html = """
        <script>
        var data = {"currentTermDate": {"year": 2025, "term": 9}};
        </script>
        """

        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_rutgers_terms()

            assert status == "success"
            assert len(terms) == 4
            assert error is None
            # Should have Fall 2025 as the first term
            assert "2025:9:NB" in terms[0]["code"]
            assert "Fall 2025" in terms[0]["description"]

    @pytest.mark.unit
    async def test_fetch_rutgers_no_term_data(self):
        """Test Rutgers terms fetch when currentTermDate not found."""
        mock_html = "<html>No term data here</html>"
        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_rutgers_terms()

            assert status == "error"
            assert terms == []
            assert error == "Could not find currentTermDate"


class TestFetchUPennTerms:
    """Tests for fetch_upenn_terms function."""

    @pytest.mark.unit
    async def test_fetch_upenn_success(self):
        """Test successful fetching of UPenn terms."""
        mock_html = """
        <select>
            <option value="202410">Fall 2024</option>
            <option value="202420">Spring 2025</option>
            <option value="12">Invalid</option>
            <option value="202430">Summer 2025</option>
        </select>
        """

        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_upenn_terms()

            assert status == "success"
            assert len(terms) <= 4
            assert error is None
            # Should only include 6-digit codes
            assert all(len(term["code"]) == 6 for term in terms)
            assert any(term["code"] == "202410" for term in terms)


class TestFetchUFTerms:
    """Tests for fetch_uf_terms function."""

    @pytest.mark.unit
    async def test_fetch_uf_success(self):
        """Test successful fetching of UF terms."""
        mock_json = [
            {"term": "2258", "termName": "Fall 2025"},
            {"term": "2251", "termName": "Spring 2025"},
            {"term": "2248", "termName": "Summer 2024"},
            {"term": "2241", "termName": "Spring 2024"},
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_json
        mock_response.raise_for_status = MagicMock()

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_uf_terms()

            assert status == "success"
            assert len(terms) == 4
            assert error is None
            assert terms[0]["code"] == "2258"
            assert terms[0]["description"] == "Fall 2025"

            # Verify headers were set correctly
            call_args = mock_client.return_value.__aenter__.return_value.get.call_args
            assert call_args[1]["headers"]["User-Agent"] == "SeatSteal/1.0"
            assert call_args[1]["headers"]["Accept"] == "application/json"

    @pytest.mark.unit
    async def test_fetch_uf_empty_response(self):
        """Test UF terms fetch with empty response."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_uf_terms()

            assert status == "error"
            assert terms == []
            assert error == "No terms found"

    @pytest.mark.unit
    async def test_fetch_uf_network_error(self):
        """Test UF terms fetch with network error."""
        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            status, terms, error = await fetch_uf_terms()

            assert status == "error"
            assert terms == []
            assert error is not None
            assert "Network error" in error

    @pytest.mark.unit
    async def test_fetch_uf_invalid_json(self):
        """Test UF terms fetch with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_response.raise_for_status = MagicMock()

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            status, terms, error = await fetch_uf_terms()

            assert status == "error"
            assert terms == []
            assert error is not None


class TestGetTermCodesEndpoint:
    """Tests for GET /api/admin/term-codes/{short_name} endpoint."""

    @pytest.mark.unit
    async def test_get_term_codes_brown_success(self, admin_client: AsyncClient):
        """Test successfully getting term codes for Brown."""
        mock_html = '<option value="202410">Fall 2024</option>'
        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            response = await admin_client.get("/api/admin/term-codes/brown")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["college"] == "brown"
            assert data["data"]["status"] in ["success", "error"]
            assert "terms" in data["data"]

    @pytest.mark.unit
    async def test_get_term_codes_unauthenticated(self, client: AsyncClient):
        """Test getting term codes without authentication."""
        response = await client.get("/api/admin/term-codes/brown")
        assert response.status_code == 401

    @pytest.mark.unit
    async def test_get_term_codes_non_admin(self, authenticated_client: AsyncClient):
        """Test getting term codes as non-admin user."""
        response = await authenticated_client.get("/api/admin/term-codes/brown")
        assert response.status_code == 403

    @pytest.mark.unit
    async def test_get_term_codes_unsupported_college(self, admin_client: AsyncClient):
        """Test getting term codes for unsupported college."""
        response = await admin_client.get("/api/admin/term-codes/unsupported")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.unit
    async def test_get_term_codes_princeton_manual(self, admin_client: AsyncClient):
        """Test getting term codes for Princeton (manual lookup required)."""
        response = await admin_client.get("/api/admin/term-codes/princeton")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "manual"
        assert "Cloudflare" in data["data"]["error"]
        assert data["data"]["terms"] == []

    @pytest.mark.unit
    async def test_get_term_codes_bu_success(self, admin_client: AsyncClient):
        """Test getting term codes for BU with complex JSON parsing."""
        search_options = {
            "search_options": {"terms": [{"strm": "2248", "descr": "Fall 2024"}]}
        }
        json_str = json.dumps(search_options)
        b64_data = base64.b64encode(json_str.encode()).decode()
        mock_html = f"atob(`{b64_data}`)"
        mock_response = MagicMock()
        mock_response.text = mock_html

        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            response = await admin_client.get("/api/admin/term-codes/bu")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["college"] == "bu"
            assert data["data"]["status"] == "success"

    @pytest.mark.unit
    async def test_get_term_codes_network_error(self, admin_client: AsyncClient):
        """Test getting term codes with network error."""
        with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network timeout")
            )

            response = await admin_client.get("/api/admin/term-codes/brown")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "error"
            assert data["data"]["error"] is not None

    @pytest.mark.unit
    async def test_get_term_codes_all_supported_colleges(
        self, admin_client: AsyncClient
    ):
        """Test that all supported colleges can be queried."""
        supported_colleges = [
            "brown",
            "bu",
            "cornell",
            "neu",
            "usc",
            "umd",
            "rutgers",
            "upenn",
            "uci",
            "uf",
        ]

        for college in supported_colleges:
            # Mock successful response for all
            mock_html = '<option value="202410">Fall 2024</option>'
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.json.return_value = [
                {"code": "202410", "description": "Fall 2024"}
            ]

            with patch("api.routes.term_codes.httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                response = await admin_client.get(f"/api/admin/term-codes/{college}")

                assert response.status_code == 200, f"Failed for college: {college}"
                data = response.json()
                assert data["success"] is True
                assert data["data"]["college"] == college
