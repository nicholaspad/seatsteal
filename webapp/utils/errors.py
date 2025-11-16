"""
Secure error handling utilities to prevent information leakage.
"""

import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def log_and_raise_500(message: str, exception: Exception) -> None:
    """
    Log the full exception details for debugging, but raise a generic error
    to prevent information leakage to clients.

    Args:
        message: A generic, user-safe error message (e.g., "Failed to fetch courses")
        exception: The actual exception that occurred

    Raises:
        HTTPException: With status 500 and the generic message
    """
    # Log the full exception for debugging/monitoring
    logger.error(f"{message}: {str(exception)}", exc_info=True)

    # Return generic message to client
    raise HTTPException(status_code=500, detail=message)


def log_and_raise(status_code: int, message: str, exception: Exception) -> None:
    """
    Log the full exception details for debugging, but raise a generic error
    with specified status code to prevent information leakage to clients.

    Args:
        status_code: HTTP status code to return
        message: A generic, user-safe error message
        exception: The actual exception that occurred

    Raises:
        HTTPException: With the specified status code and generic message
    """
    # Log the full exception for debugging/monitoring
    logger.error(f"{message}: {str(exception)}", exc_info=True)

    # Return generic message to client
    raise HTTPException(status_code=status_code, detail=message)


def sanitize_error_message(error_msg: str) -> str:
    """
    Sanitize an error message to remove potentially sensitive information.

    This removes:
    - File paths
    - Stack traces
    - Internal variable names
    - Database connection strings
    - API keys or secrets

    Args:
        error_msg: The original error message

    Returns:
        A sanitized version of the error message
    """
    # List of patterns that indicate sensitive information
    sensitive_patterns = [
        "Traceback",
        "File ",
        "/Users/",
        "/home/",
        "password=",
        "secret=",
        "key=",
        "postgresql://",
        "mysql://",
        "sqlite://",
        "redis://",
        "aws_access_key",
        "aws_secret",
    ]

    error_lower = error_msg.lower()
    for pattern in sensitive_patterns:
        if pattern.lower() in error_lower:
            return "An internal error occurred"

    return error_msg
