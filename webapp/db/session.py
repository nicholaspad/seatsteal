from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from .connection import engine

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Model))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()