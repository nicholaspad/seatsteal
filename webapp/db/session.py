from typing import Generator
from sqlalchemy.orm import Session, sessionmaker
from db.connection import engine

# Create sync session factory
# - expire_on_commit=False: Prevents re-querying after commit
# - autoflush=True: Automatically flush before queries (default, explicit for clarity)
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=True,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/example")
        async def example(db: Session = Depends(get_db)):
            result = db.execute(select(Model))
            return result.scalars().all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
