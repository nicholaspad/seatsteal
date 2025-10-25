from sqlalchemy import create_engine, Engine
from config import settings

# Create sync database engine with psycopg2 (works with PgBouncer)
engine: Engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)


def init_db():
    """Initialize database connection on application startup"""
    # Test connection
    with engine.begin() as conn:
        pass


def close_db():
    """Close database connections on application shutdown"""
    engine.dispose()
