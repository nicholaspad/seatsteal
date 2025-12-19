"""Tests for security headers middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from api.middleware.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.mark.unit
    async def test_adds_all_security_headers(self):
        """Test middleware adds all required security headers."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify all security headers are present
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert (
            response.headers["Content-Security-Policy"]
            == "default-src 'none'; frame-ancestors 'none'"
        )
        assert response.headers["X-DNS-Prefetch-Control"] == "off"

    @pytest.mark.unit
    async def test_adds_cache_control_headers_when_not_present(self):
        """Test middleware adds cache control headers when not already set."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify cache control headers are added
        assert (
            response.headers["Cache-Control"]
            == "no-store, no-cache, must-revalidate, private"
        )
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"

    @pytest.mark.unit
    async def test_preserves_existing_cache_control_headers(self):
        """Test middleware preserves existing Cache-Control headers."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)
        # Pre-set Cache-Control header (e.g., for static content)
        mock_response.headers["Cache-Control"] = "public, max-age=3600"

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify existing Cache-Control is preserved
        assert response.headers["Cache-Control"] == "public, max-age=3600"
        # Pragma and Expires should not be added when Cache-Control exists
        assert "Pragma" not in response.headers
        assert "Expires" not in response.headers

    @pytest.mark.unit
    async def test_applies_to_json_response(self):
        """Test middleware applies headers to JSON responses."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = JSONResponse(content={"message": "test"}, status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify security headers are applied to JSON response
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert (
            response.headers["Content-Security-Policy"]
            == "default-src 'none'; frame-ancestors 'none'"
        )

    @pytest.mark.unit
    async def test_applies_to_error_responses(self):
        """Test middleware applies headers to error responses."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = JSONResponse(content={"error": "Not found"}, status_code=404)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify security headers are applied even to error responses
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-DNS-Prefetch-Control"] == "off"

    @pytest.mark.unit
    async def test_x_frame_options_denies_framing(self):
        """Test X-Frame-Options prevents clickjacking attacks."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # DENY prevents the page from being displayed in any frame
        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.unit
    async def test_content_type_options_prevents_mime_sniffing(self):
        """Test X-Content-Type-Options prevents MIME type sniffing."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # nosniff prevents MIME type sniffing
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.unit
    async def test_csp_restrictive_policy(self):
        """Test Content-Security-Policy is restrictive for API responses."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify CSP is restrictive
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    @pytest.mark.unit
    async def test_referrer_policy_limits_information_disclosure(self):
        """Test Referrer-Policy limits information disclosure."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # strict-origin-when-cross-origin provides good balance of privacy and functionality
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.unit
    async def test_dns_prefetch_control_disabled(self):
        """Test X-DNS-Prefetch-Control disables DNS prefetching."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify DNS prefetching is disabled for privacy
        assert response.headers["X-DNS-Prefetch-Control"] == "off"

    @pytest.mark.unit
    async def test_cache_control_for_sensitive_data(self):
        """Test Cache-Control prevents caching of sensitive API responses."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = JSONResponse(
            content={"user": "data", "sensitive": "info"}, status_code=200
        )

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify cache control prevents caching of sensitive data
        cache_control = response.headers["Cache-Control"]
        assert "no-store" in cache_control
        assert "no-cache" in cache_control
        assert "must-revalidate" in cache_control
        assert "private" in cache_control

    @pytest.mark.unit
    async def test_preserves_response_content(self):
        """Test middleware preserves response content and status."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        original_content = {"data": "test", "id": 123}
        mock_response = JSONResponse(content=original_content, status_code=201)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Verify response content and status are preserved
        assert response.status_code == 201
        # Headers added but content unchanged
        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.unit
    async def test_applies_to_all_http_methods(self):
        """Test middleware applies to all HTTP methods."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            mock_request = MagicMock(spec=Request)
            mock_request.method = method
            mock_response = Response(content="test", status_code=200)

            async def call_next(request):
                return mock_response

            response = await middleware.dispatch(mock_request, call_next)

            # Verify headers are applied regardless of HTTP method
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.unit
    async def test_security_headers_order_independence(self):
        """Test that security headers work correctly regardless of order."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="test", status_code=200)

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # All headers should be present
        expected_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Content-Security-Policy",
            "X-DNS-Prefetch-Control",
            "Cache-Control",
            "Pragma",
            "Expires",
        ]

        for header in expected_headers:
            assert header in response.headers
