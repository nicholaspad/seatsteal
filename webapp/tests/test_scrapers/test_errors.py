"""Tests for shared scraper exception formatting."""

import httpx

from scraper.utils.errors import format_exception_message


class _EmptyStrError(Exception):
    """Mirrors httpx/httpcore transport disconnects whose str(e) is empty."""

    def __str__(self) -> str:
        return ""


def test_format_empty_str_exception_includes_type_and_repr():
    """Empty str(e) must still identify the failure by type and repr."""
    exc = _EmptyStrError()

    formatted = format_exception_message(exc)

    assert type(exc).__name__ in formatted
    assert repr(exc) in formatted
    assert formatted.strip() != ""
    assert "Unknown error" not in formatted


def test_format_named_http_error_keeps_message():
    """Named HTTP errors keep their original message and include the type."""
    request = httpx.Request("GET", "https://example.edu/api")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError(
        "Server error '503 Service Unavailable' for url 'https://example.edu/api'",
        request=request,
        response=response,
    )

    formatted = format_exception_message(exc)

    assert "HTTPStatusError" in formatted
    assert "503" in formatted
    assert str(exc).strip() != ""
    assert str(exc) in formatted


def test_format_includes_cause_when_present():
    """Cause/context is appended so empty wrappers still show the root error."""
    try:
        try:
            raise ConnectionError("peer closed")
        except ConnectionError as inner:
            raise _EmptyStrError() from inner
    except _EmptyStrError as exc:
        formatted = format_exception_message(exc)

    assert "_EmptyStrError" in formatted
    assert "ConnectionError" in formatted
    assert "peer closed" in formatted


def test_format_none_is_empty():
    """None is the only input that formats to an empty string."""
    assert format_exception_message(None) == ""


def test_format_remote_protocol_error_with_empty_str():
    """httpx transport disconnects with empty str still format usefully."""
    exc = httpx.RemoteProtocolError("")

    formatted = format_exception_message(exc)

    assert "RemoteProtocolError" in formatted
    assert formatted.strip() != ""
    assert "Unknown error" not in formatted


def test_format_bu_fetch_error_keeps_http_status_and_size():
    """BuFetchError must still carry HTTP status and response size after formatting."""
    from scraper.scrapers.bu import BuFetchError

    exc = BuFetchError(
        "BU page 1 HTTP 502 response_size=145 content_type=text/html term=2268"
    )
    formatted = format_exception_message(exc)

    assert "BuFetchError" in formatted
    assert "HTTP 502" in formatted
    assert "response_size=145" in formatted
    assert str(exc) in formatted
