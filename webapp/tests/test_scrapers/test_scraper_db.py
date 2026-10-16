"""Tests that scraper DB timeouts stay isolated from the FastAPI engine."""

from scraper.db import (
    SCRAPER_CONNECT_ARGS,
    SCRAPER_CONNECT_TIMEOUT_SECONDS,
    SCRAPER_POOL_TIMEOUT_SECONDS,
    SCRAPER_STATEMENT_TIMEOUT_MS,
    scraper_engine,
)


def test_scraper_engine_is_not_the_api_engine():
    from db.connection import engine as api_engine

    assert scraper_engine is not api_engine


def test_scraper_connect_args_include_timeouts_and_keepalives():
    assert SCRAPER_CONNECT_ARGS["connect_timeout"] == SCRAPER_CONNECT_TIMEOUT_SECONDS
    assert (
        SCRAPER_CONNECT_ARGS["options"]
        == f"-c statement_timeout={SCRAPER_STATEMENT_TIMEOUT_MS}"
    )
    assert SCRAPER_STATEMENT_TIMEOUT_MS == 120_000
    assert SCRAPER_CONNECT_ARGS["keepalives"] == 1
    assert SCRAPER_CONNECT_ARGS["keepalives_idle"] == 30
    assert SCRAPER_CONNECT_ARGS["keepalives_interval"] == 10
    assert SCRAPER_CONNECT_ARGS["keepalives_count"] == 5


def test_scraper_engine_pool_timeout():
    assert scraper_engine.pool.timeout() == SCRAPER_POOL_TIMEOUT_SECONDS


def test_api_engine_keeps_five_minute_statement_timeout():
    """FastAPI / Stripe webhook engine must not inherit the 120s scraper cap."""
    import inspect
    from db import connection as api_connection

    source = inspect.getsource(api_connection)
    assert "statement_timeout=300000" in source
    assert "statement_timeout=120000" not in source
    assert "connect_timeout" not in source
