"""
Tests for authentication endpoints.

This test suite validates the magic link authentication flow:
1. Requesting a magic link (creates or updates user with token)
2. Verifying the token (authenticates user and clears token for one-time use)

The fixtures (async_client, db) handle all cleanup automatically via try/finally blocks.
Each test gets a fresh in-memory SQLite database that's destroyed after the test.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_request_magic_link_new_user(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Request magic link for a NEW user
    
    What happens:
    1. User doesn't exist yet in database
    2. POST /api/auth/request-magic-link creates the user
    3. Sets magic_link_token (random UUID hex)
    4. Sets token_expires_at (15 minutes from now)
    5. Returns 200 with confirmation message
    
    Verifies:
    - API returns correct email and success message
    - User record is created in database
    - Token and expiry are set
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request to create magic link
        response = await async_client.post(
            "/api/auth/request-magic-link",
            json={"email": "newuser@example.com"}
        )
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "Magic link sent" in data["message"]
        
        # Verify database state: user was created with token
        result = await db.execute(
            select(User).where(User.email == "newuser@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None, "User should be created in database"
        assert user.magic_link_token is not None, "Token should be generated"
        assert user.magic_link_expires_at is not None, "Expiry should be set"
        
    except Exception as e:
        # If test fails, fixture still cleans up DB
        raise e


@pytest.mark.asyncio
async def test_request_magic_link_existing_user(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Request magic link for an EXISTING user
    
    What happens:
    1. User already exists in database
    2. POST /api/auth/request-magic-link finds the existing user
    3. UPDATES their magic_link_token (new token)
    4. UPDATES their token_expires_at (new expiry)
    5. Does NOT create duplicate user
    
    Verifies:
    - No duplicate users created (still only 1 user with that email)
    - Same user ID (proves it's an update, not a new user)
    - Token is updated (not None)
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create existing user in database
        user = User(email="existing@example.com")
        db.add(user)
        await db.commit()
        old_id = user.id  # Save ID to verify no duplication
        
        # Make API request for same email
        response = await async_client.post(
            "/api/auth/request-magic-link",
            json={"email": "existing@example.com"}
        )
        
        # Verify API response
        assert response.status_code == 200
        
        # Verify database state: user updated, not duplicated
        result = await db.execute(
            select(User).where(User.email == "existing@example.com")
        )
        users = result.scalars().all()
        assert len(users) == 1, "Should not create duplicate user"
        assert users[0].id == old_id, "Should update existing user, not create new one"
        assert users[0].magic_link_token is not None, "Token should be updated"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_verify_token_valid(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Verify a VALID magic link token
    
    What happens:
    1. User exists with a valid token (not expired)
    2. POST /api/auth/verify-token checks token validity
    3. Token matches and hasn't expired
    4. Returns 200 with user info and session token
    5. CLEARS the magic_link_token (one-time use security)
    6. CLEARS the token_expires_at
    
    Verifies:
    - API returns user email, user_id, and session token
    - Magic link token is cleared from database (can't reuse)
    - Expiry is also cleared
    
    This implements one-time use security: token is destroyed after first use.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create user with valid (non-expired) token
        user = User(email="test@example.com")
        user.magic_link_token = uuid4().hex
        user.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)
        db.add(user)
        await db.commit()
        saved_token = user.magic_link_token
        
        # Make API request to verify token
        response = await async_client.post(
            "/api/auth/verify-token",
            json={"token": saved_token}
        )
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["user_id"] == str(user.id)
        assert data["access_token"] is not None, "Should return session token"
        # Phase 1: access_token is user_id (will be JWT in Phase 2)
        assert data["access_token"] == str(user.id), "Session token should match user_id"
        
        # Verify database state: magic link token cleared (one-time use)
        await db.refresh(user)
        assert user.magic_link_token is None, "Magic link token should be cleared after use"
        assert user.magic_link_expires_at is None, "Expiry should be cleared"
        
    except Exception as e:
        raise e
    finally:
        pass


@pytest.mark.asyncio
async def test_verify_token_invalid_empty_db(async_client: AsyncClient):
    """
    Test: Verify an INVALID token (NO users in database)
    
    What happens:
    1. Database is empty (no users exist)
    2. POST /api/auth/verify-token with random token
    3. Query finds no user with this token
    4. Returns 401 Unauthorized with error message
    
    Verifies:
    - Cannot authenticate when DB is empty
    - Returns proper HTTP status (401)
    - Error message mentions "Invalid token"
    
    Security: Prevents brute force attacks (would need to guess valid token).
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request with fake token (DB is empty)
        response = await async_client.post(
            "/api/auth/verify-token",
            json={"token": "invalid-token-12345"}
        )
        
        # Verify rejection
        assert response.status_code == 401, "Should reject invalid token"
        assert "Invalid token" in response.json()["detail"]
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_verify_token_invalid_with_users(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Verify an INVALID token (users exist but token doesn't match)
    
    What happens:
    1. Database has users with their own tokens
    2. POST /api/auth/verify-token with token that doesn't match any user
    3. Query finds no user with this specific token
    4. Returns 401 Unauthorized with error message
    
    Verifies:
    - Cannot authenticate with wrong token even if users exist
    - Returns proper HTTP status (401)
    - Error message mentions "Invalid token"
    
    Security: Token must exactly match - can't use another user's token or random token.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create users with their own valid tokens
        user1 = User(email="user1@example.com")
        user1.magic_link_token = uuid4().hex
        user1.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        user2 = User(email="user2@example.com")
        user2.magic_link_token = uuid4().hex
        user2.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        db.add_all([user1, user2])
        await db.commit()
        
        # Make API request with token that doesn't match either user
        response = await async_client.post(
            "/api/auth/verify-token",
            json={"token": "completely-different-token-12345"}
        )
        
        # Verify rejection
        assert response.status_code == 401, "Should reject invalid token"
        assert "Invalid token" in response.json()["detail"]
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_verify_token_expired(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Verify an EXPIRED token
    
    What happens:
    1. User has a token, but token_expires_at is in the past
    2. POST /api/auth/verify-token finds the token
    3. Checks expiry: token_expires_at < now → EXPIRED
    4. Returns 401 with "expired" error message
    5. CLEARS the expired token from database (cleanup)
    
    Verifies:
    - Expired tokens cannot be used (security)
    - Returns 401 with expiry error message
    - Token is cleared from database (automatic cleanup)
    
    Security: 15-minute window for magic links prevents stale links from working.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create user with expired token (1 minute ago)
        user = User(email="expired@example.com")
        user.magic_link_token = uuid4().hex
        user.magic_link_expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.add(user)
        await db.commit()
        expired_token = user.magic_link_token
        
        # Make API request with expired token
        response = await async_client.post(
            "/api/auth/verify-token",
            json={"token": expired_token}
        )
        
        # Verify rejection
        assert response.status_code == 401, "Should reject expired token"
        assert "expired" in response.json()["detail"].lower()
        
        # Verify database state: expired token was cleared
        await db.refresh(user)
        assert user.magic_link_token is None, "Expired token should be cleared"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_request_magic_link_invalid_email(async_client: AsyncClient):
    """
    Test: Request magic link with INVALID email format
    
    What happens:
    1. POST /api/auth/request-magic-link with malformed email
    2. Pydantic validation catches invalid email format
    3. Returns 422 Unprocessable Entity (validation error)
    4. Never hits database (fails at validation layer)
    
    Verifies:
    - Input validation works before database operations
    - Invalid emails are rejected with 422
    
    Pydantic EmailStr validates format: must have @ symbol, domain, etc.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request with malformed email
        response = await async_client.post(
            "/api/auth/request-magic-link",
            json={"email": "not-an-email"}
        )
        
        # Verify validation rejection
        assert response.status_code == 422, "Should reject invalid email format"
        
    except Exception as e:
        raise e
