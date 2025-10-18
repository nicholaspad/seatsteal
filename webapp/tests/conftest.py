"""Shared test fixtures and configuration for all tests."""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

import sys
import os
from pathlib import Path

# Set environment variables for testing BEFORE any imports
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test_key"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_123"
os.environ["PYTHON_ENV"] = "test"

# Add parent of webapp to path so we can import webapp as a package
webapp_parent = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_parent))

# Now import from webapp package
from webapp.app import app
from webapp.db.session import get_db
from webapp.models.base import Base
from webapp.models.user import Profile
from webapp.models.college import College
from webapp.models.course import Course
from webapp.models.class_model import Class
from webapp.models.enrollment import Enrollment
from webapp.models.subscription import Subscription
from webapp.models.stripe_customer import StripeCustomer
from webapp.models.stripe_subscription import StripeSubscription
from webapp.config import settings


# Test database URL - Use PostgreSQL test database
# Format: postgresql+asyncpg://user:password@host:port/database
# Default: postgresql+asyncpg://[current_user]@localhost:5432/seatsteal_test
import getpass

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+asyncpg://{getpass.getuser()}@localhost:5432/seatsteal_test",
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.

    Uses PostgreSQL test database. Tables are created before each test
    and dropped after each test for complete isolation.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables (including PostgreSQL-specific features)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    # Clean up: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def mock_supabase_user():
    """Mock Supabase user response."""
    user_id = str(uuid4())
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.email = "test@example.edu"

    mock_response = MagicMock()
    mock_response.user = mock_user

    return mock_response, user_id


@pytest.fixture
def mock_supabase_admin_user():
    """Mock Supabase admin user response."""
    user_id = str(uuid4())
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.email = "admin@example.edu"

    mock_response = MagicMock()
    mock_response.user = mock_user

    return mock_response, user_id


@pytest.fixture
async def test_college(test_db: AsyncSession) -> College:
    """Create a test college."""
    college = College(
        name="Test University",
        short_name="TU",
        is_active=True,
    )
    test_db.add(college)
    await test_db.commit()
    await test_db.refresh(college)
    return college


@pytest.fixture
async def test_user(
    test_db: AsyncSession, test_college: College, mock_supabase_user
) -> Profile:
    """Create a test user."""
    _, user_id = mock_supabase_user
    user = Profile(
        id=user_id,
        email="test@example.edu",
        phone="+1234567890",
        college_id=test_college.id,
        role="user",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_admin_user(
    test_db: AsyncSession, test_college: College, mock_supabase_admin_user
) -> Profile:
    """Create a test admin user."""
    _, user_id = mock_supabase_admin_user
    admin = Profile(
        id=user_id,
        email="admin@example.edu",
        phone="+1234567891",
        college_id=test_college.id,
        role="admin",
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def test_course(test_db: AsyncSession, test_college: College) -> Course:
    """Create a test course."""
    course = Course(
        college_id=test_college.id,
        course_code="CS101",
        title="Introduction to Computer Science",
        is_active=True,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.fixture
async def test_class(test_db: AsyncSession, test_course: Course) -> Class:
    """Create a test class."""
    test_class = Class(
        course_id=test_course.id,
        class_number="12345",
        section_code="A",
        is_active=True,
    )
    test_db.add(test_class)
    await test_db.commit()
    await test_db.refresh(test_class)
    return test_class


@pytest.fixture
async def test_enrollment(
    test_db: AsyncSession, test_class: Class, test_course: Course
) -> Enrollment:
    """Create a test enrollment."""
    enrollment = Enrollment(
        class_id=test_class.class_id,
        college_id=test_course.college_id,
        enrollment_status="open",
        scraped_at=datetime.utcnow(),
    )
    test_db.add(enrollment)
    await test_db.commit()
    await test_db.refresh(enrollment)
    return enrollment


@pytest.fixture
async def test_subscription(
    test_db: AsyncSession,
    test_user: Profile,
    test_class: Class,
    test_college: College,
) -> Subscription:
    """Create a test subscription."""
    subscription = Subscription(
        user_id=test_user.id,
        class_id=test_class.class_id,
        college_id=test_college.id,
        is_active=True,
        notification_count=0,
    )
    test_db.add(subscription)
    await test_db.commit()
    await test_db.refresh(subscription)
    return subscription


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("webapp.api.middleware.auth.supabase") as mock:
        mock_auth = MagicMock()
        mock.auth = mock_auth
        yield mock


@pytest.fixture
def mock_stripe():
    """Mock Stripe client."""
    with patch("webapp.utils.stripe_utils.stripe") as mock:
        yield mock


@pytest.fixture
async def client(
    test_db: AsyncSession, mock_supabase
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database dependency override."""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(
    client: AsyncClient,
    test_user: Profile,
    mock_supabase,
    mock_supabase_user,
) -> AsyncClient:
    """Create an authenticated test client."""
    mock_response, _ = mock_supabase_user
    mock_supabase.auth.get_user.return_value = mock_response

    client.headers.update({"Authorization": "Bearer test_token"})
    return client


@pytest.fixture
async def admin_client(
    client: AsyncClient,
    test_admin_user: Profile,
    mock_supabase,
    mock_supabase_admin_user,
) -> AsyncClient:
    """Create an authenticated admin test client."""
    mock_response, _ = mock_supabase_admin_user
    mock_supabase.auth.get_user.return_value = mock_response

    client.headers.update({"Authorization": "Bearer admin_token"})
    return client


# Additional helper fixtures for test data


@pytest.fixture
async def multiple_courses(test_db: AsyncSession, test_college: College):
    """Create multiple test courses."""
    courses = []
    for i in range(5):
        course = Course(
            college_id=test_college.id,
            course_code=f"CS{100 + i}",
            title=f"Test Course {i}",
            is_active=True,
        )
        test_db.add(course)
        courses.append(course)

    await test_db.commit()
    for course in courses:
        await test_db.refresh(course)

    return courses


@pytest.fixture
async def multiple_classes(test_db: AsyncSession, test_course: Course):
    """Create multiple test classes."""
    classes = []
    for i in range(3):
        test_class = Class(
            course_id=test_course.id,
            class_number=str(12345 + i),
            section_code=chr(65 + i),  # A, B, C
            is_active=True,
        )
        test_db.add(test_class)
        classes.append(test_class)

    await test_db.commit()
    for test_class in classes:
        await test_db.refresh(test_class)

    return classes
