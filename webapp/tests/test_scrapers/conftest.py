"""Shared fixtures and utilities for scraper tests."""

import json
from unittest.mock import MagicMock


def create_mock_response(data, status_code=200):
    """
    Create a mock HTTP response with both json() and content set correctly.

    Args:
        data: The data to return from json() and encode as content
        status_code: HTTP status code (default 200)

    Returns:
        MagicMock configured as an HTTP response
    """
    mock_response = MagicMock()
    mock_response.json.return_value = data
    mock_response.content = json.dumps(data).encode("utf-8")
    mock_response.status_code = status_code
    mock_response.raise_for_status = MagicMock()
    return mock_response
