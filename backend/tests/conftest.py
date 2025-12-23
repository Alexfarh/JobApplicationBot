"""
Pytest fixtures for testing.
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Import database module BEFORE app to allow override
import app.database
from app.database import Base, get_db
# Import ALL models so Base.metadata knows about all tables
from app.models.user import User
from app.models.application_run import ApplicationRun
from app.models.application_task import ApplicationTask
from app.models.approval_request import ApprovalRequest
from app.models.job_posting import JobPosting

# Now import app (after we can override database)
from app.main import app as fastapi_app


# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database for each test.
    Ensures cleanup happens even if test fails.
    """
    # Create async engine for test database
    # Use StaticPool to keep single connection alive and reuse it
    # This ensures all sessions see the same in-memory database
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables FIRST
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Verify: StaticPool reuses a single connection for all operations
    # This ensures only ONE in-memory database exists per test
    assert isinstance(test_engine.pool, StaticPool), f"Expected StaticPool, got {type(test_engine.pool)}"
    
    # THEN replace the app's engine and sessionmaker
    # This ensures get_db() uses sessions connected to DB with tables
    original_engine = app.database.engine
    original_sessionmaker = app.database.AsyncSessionLocal
    
    app.database.engine = test_engine
    app.database.AsyncSessionLocal = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create session for direct test use
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    session = async_session()
    
    try:
        yield session
    finally:
        # Cleanup strategy: Try each step independently
        # For in-memory DB, engine.dispose() is the ultimate cleanup
        
        # Step 1: Close session
        try:
            await session.close()
        except Exception as e:
            print(f"Warning: Failed to close session: {e}")
        
        # Step 2: Drop tables (best effort)
        try:
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception as e:
            print(f"Warning: Failed to drop tables: {e}")
            print("In-memory DB will be destroyed on engine disposal")
        
        # Step 3: Dispose test engine
        try:
            await test_engine.dispose()
        except Exception as e:
            print(f"Warning: Failed to dispose engine: {e}")
            # At this point, rely on Python's garbage collector
        
        # Step 4: Restore original engine
        app.database.engine = original_engine
        app.database.AsyncSessionLocal = original_sessionmaker


@pytest_asyncio.fixture
async def async_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing endpoints.
    
    The db fixture already replaced app.database.engine with test engine,
    so all endpoints will automatically use the test database.
    """
    transport = ASGITransport(app=fastapi_app)
    
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True  # Follow 307 redirects for trailing slashes
    ) as client:
        yield client


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """
    Create a test user for tests that need authentication.
    """
    user = User(email="testuser@example.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
