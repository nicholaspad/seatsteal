from sqlalchemy import create_engine, Engine
from config import settings

# Create sync database engine with psycopg2 (works with PgBouncer)
engine: Engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "options": "-c statement_timeout=300000",  # 5 minute timeout for large batch operations
        "keepalives": 1,  # Enable TCP keepalive
        "keepalives_idle": 30,  # Start keepalive after 30s idle
        "keepalives_interval": 10,  # Send keepalive every 10s
        "keepalives_count": 5,  # Drop connection after 5 failed keepalives
    },
)


def init_db():
    """Initialize database connection on application startup"""
    # Test connection
    with engine.begin() as conn:
        pass


def close_db():
    """Close database connections on application shutdown"""
    engine.dispose()
