from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from ..config import settings

# Create async database engine
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.PYTHON_ENV == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)


async def init_db():
    """Initialize database connection on application startup"""
    # Test connection
    async with engine.begin() as conn:
        pass


async def close_db():
    """Close database connections on application shutdown"""
    await engine.dispose()