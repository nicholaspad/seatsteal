"""Shared exception formatting for scraper error messages."""

from typing import Optional


def format_exception_message(exc: Optional[BaseException]) -> str:
    """Format an exception so empty ``str(e)`` still identifies the failure.

    httpx/httpcore transport disconnects frequently have empty ``str(e)`` even
    when ``type(e).__name__`` and ``repr(e)`` are useful. Named errors keep
    their original message, always prefixed with the exception type.

    Returns a non-empty string whenever ``exc`` is not ``None``.
    """
    if exc is None:
        return ""

    message = str(exc).strip()
    exc_type = type(exc).__name__
    exc_repr = repr(exc)

    if message:
        detail = f"{exc_type}: {message}"
    else:
        detail = f"{exc_type}: {exc_repr}"

    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        cause_msg = str(cause).strip() or repr(cause)
        cause_type = type(cause).__name__
        if cause_msg and cause_msg not in detail:
            detail = f"{detail} (cause: {cause_type}: {cause_msg})"

    return detail
