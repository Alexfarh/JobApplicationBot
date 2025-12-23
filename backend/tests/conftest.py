"""
Pytest fixtures for testing.
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User


# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database for each test.
    Ensures cleanup happens even if test fails.
    """
    # Create async engine for test database
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
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
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception as e:
            print(f"Warning: Failed to drop tables: {e}")
            print("In-memory DB will be destroyed on engine disposal")
        
        # Step 3: Dispose engine (destroys in-memory DB)
        try:
            await engine.dispose()
        except Exception as e:
            print(f"Warning: Failed to dispose engine: {e}")
            # At this point, rely on Python's garbage collector


@pytest_asyncio.fixture
async def async_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing endpoints.
    
    Overrides the get_db dependency to use the test database.
    Ensures dependency overrides are cleared even if test fails.
    """
    async def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        # Always clear dependency overrides (cleanup even on test failure)
        app.dependency_overrides.clear()


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
