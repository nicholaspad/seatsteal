from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from uuid import uuid4
from ..config import settings

# Create async database engine
engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=settings.is_development,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },  # Required for pgbouncer compatibility
)


async def init_db():
    """Initialize database connection on application startup"""
    # Test connection
    async with engine.begin() as conn:
        pass


async def close_db():
    """Close database connections on application shutdown"""
    await engine.dispose()
