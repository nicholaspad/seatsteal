"""
Scraper-process database engine.

Timeouts here apply ONLY to scraper workers. The FastAPI API (including
Stripe webhook writes) continues to use db.connection.engine unchanged.
"""

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings

# Cautious per-statement cap. Upserts are already chunked in ScraperService
# so a single statement should not need the API engine's 5-minute budget.
# These timeouts also rescue a stuck sync query: scrape code awaits HTTP
# but runs SQLAlchemy synchronously, so asyncio.wait_for cannot fire until
# the driver returns. statement_timeout + keepalives force that return.
SCRAPER_STATEMENT_TIMEOUT_MS = 120_000
SCRAPER_CONNECT_TIMEOUT_SECONDS = 10
SCRAPER_POOL_TIMEOUT_SECONDS = 30
SCRAPER_KEEPALIVES_IDLE = 30
SCRAPER_KEEPALIVES_INTERVAL = 10
SCRAPER_KEEPALIVES_COUNT = 5

SCRAPER_CONNECT_ARGS = {
    "connect_timeout": SCRAPER_CONNECT_TIMEOUT_SECONDS,
    "options": f"-c statement_timeout={SCRAPER_STATEMENT_TIMEOUT_MS}",
    "keepalives": 1,
    "keepalives_idle": SCRAPER_KEEPALIVES_IDLE,
    "keepalives_interval": SCRAPER_KEEPALIVES_INTERVAL,
    "keepalives_count": SCRAPER_KEEPALIVES_COUNT,
}

# Dedicated engine so scraper socket/statement timeouts cannot affect the API.
scraper_engine: Engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=SCRAPER_POOL_TIMEOUT_SECONDS,
    connect_args=SCRAPER_CONNECT_ARGS,
)

ScraperSessionLocal = sessionmaker(
    bind=scraper_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=True,
)
