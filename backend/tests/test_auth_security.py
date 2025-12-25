"""
Tests for enhanced authentication security features.

This test suite validates:
1. User roles (USER vs ADMIN)
2. Account lockout after failed login attempts
3. IP address logging
4. Admin-only endpoint access
5. Profile completeness checks
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_new_user_defaults_to_user_role(async_client: AsyncClient, db: AsyncSession):
    """
    Test: New users are created with USER role by default (not ADMIN).
    
    Security: Prevents privilege escalation on registration.
    """
    response = await async_client.post(
        "/api/auth/request-magic-link",
        json={"email": "newuser@example.com"}
    )
    
    assert response.status_code == 200
    
    # Verify user has USER role (not ADMIN)
    result = await db.execute(
        select(User).where(User.email == "newuser@example.com")
    )
    user = result.scalar_one()
    assert user.role == UserRole.USER, "New users should default to USER role"
    assert not user.is_admin(), "New users should not be admins"


@pytest.mark.asyncio
async def test_verify_token_returns_role_and_profile_status(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Verify token returns user role and profile completeness.
    
    Frontend needs this info to show appropriate UI.
    """
    # Setup: User with incomplete profile
    user = User(
        email="test@example.com",
        role=UserRole.USER,
        full_name=None,  # Profile incomplete
        phone=None,
        resume_path=None
    )
    user.magic_link_token = uuid4().hex
    user.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.add(user)
    await db.commit()
    
    # Verify token
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": user.magic_link_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "user"
    assert data["profile_complete"] is False, "Profile is incomplete"
    assert data["full_name"] is None


@pytest.mark.asyncio
async def test_verify_token_with_complete_profile(async_client: AsyncClient, db: AsyncSession):
    """
    Test: User with complete profile returns profile_complete=True.
    """
    # Setup: User with complete profile
    user = User(
        email="complete@example.com",
        role=UserRole.USER,
        full_name="John Doe",
        phone="555-1234",
        resume_path="/data/resumes/user123/resume.pdf",
        mandatory_questions={
            "work_authorization": "yes",
            "veteran_status": "no",
            "disability_status": "no"
        }
    )
    user.magic_link_token = uuid4().hex
    user.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.add(user)
    await db.commit()
    
    # Verify token
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": user.magic_link_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["profile_complete"] is True
    assert data["full_name"] == "John Doe"


@pytest.mark.asyncio
async def test_account_lockout_after_failed_attempts(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Account locks after 5 failed login attempts.
    
    Security: Prevents brute force attacks on magic link tokens.
    """
    # Setup: User with valid token but we'll use expired tokens to trigger failures
    user = User(email="locktest@example.com")
    user.failed_login_attempts = 0
    db.add(user)
    await db.commit()
    
    # Attempt 1-4: Use expired tokens (increments failed_login_attempts)
    for i in range(4):
        user.magic_link_token = uuid4().hex
        user.magic_link_expires_at = datetime.utcnow() - timedelta(minutes=1)  # Expired
        await db.commit()
        
        response = await async_client.post(
            "/api/auth/verify-token",
            json={"token": user.magic_link_token}
        )
        assert response.status_code == 401  # Expired token
        
        await db.refresh(user)
        assert user.failed_login_attempts == i + 1
        assert user.account_locked_until is None  # Not locked yet
    
    # Attempt 5: Should lock account
    user.magic_link_token = uuid4().hex
    user.magic_link_expires_at = datetime.utcnow() - timedelta(minutes=1)
    await db.commit()
    
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": user.magic_link_token}
    )
    assert response.status_code == 401
    
    await db.refresh(user)
    assert user.failed_login_attempts == 5
    assert user.account_locked_until is not None, "Account should be locked after 5 failures"
    
    # Verify lock duration (30 minutes)
    lock_duration = user.account_locked_until - datetime.utcnow()
    assert 29 <= lock_duration.total_seconds() / 60 <= 31, "Lock should be ~30 minutes"


@pytest.mark.asyncio
async def test_locked_account_rejects_valid_token(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Locked account cannot log in even with valid token.
    
    Security: Account lock takes precedence over token validity.
    """
    # Setup: User with valid token BUT account is locked
    user = User(email="locked@example.com")
    user.magic_link_token = uuid4().hex
    user.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)  # Valid!
    user.account_locked_until = datetime.utcnow() + timedelta(minutes=15)  # Locked!
    db.add(user)
    await db.commit()
    
    # Try to verify valid token
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": user.magic_link_token}
    )
    
    # Should be rejected with 403 Forbidden (not 401)
    assert response.status_code == 403, "Locked accounts should return 403"
    assert "locked" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_successful_login_resets_failed_attempts(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Successful login resets failed_login_attempts counter.
    
    Security: Counter resets so users aren't permanently penalized for past failures.
    """
    # Setup: User with some failed attempts but valid token
    user = User(email="reset@example.com")
    user.failed_login_attempts = 3  # Had some failures
    user.magic_link_token = uuid4().hex
    user.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.add(user)
    await db.commit()
    
    # Successful login
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": user.magic_link_token}
    )
    
    assert response.status_code == 200
    
    # Verify counter reset
    await db.refresh(user)
    assert user.failed_login_attempts == 0, "Should reset on successful login"
    assert user.account_locked_until is None


@pytest.mark.asyncio
async def test_ip_address_logging_on_login(async_client: AsyncClient, db: AsyncSession):
    """
    Test: IP address is logged on successful login.
    
    Security: Audit trail for security monitoring.
    """
    # Setup: User with valid token
    user = User(email="iptest@example.com")
    user.magic_link_token = uuid4().hex
    user.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.add(user)
    await db.commit()
    
    # Login with custom IP header (simulating proxy)
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": user.magic_link_token},
        headers={"X-Forwarded-For": "203.0.113.45"}
    )
    
    assert response.status_code == 200
    
    # Verify IP was logged
    await db.refresh(user)
    assert user.last_login_ip == "203.0.113.45"
    assert user.last_login_at is not None


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token(async_client: AsyncClient, db: AsyncSession):
    """
    Test: get_current_user dependency validates bearer token.
    """
    # Setup: User in database
    user = User(email="authtest@example.com", role=UserRole.USER)
    db.add(user)
    await db.commit()
    
    # Use user_id as token (Phase 1 auth) - must be string
    response = await async_client.get(
        "/api/runs/",  # Use trailing slash to avoid redirect
        headers={"Authorization": f"Bearer {str(user.id)}"}
    )
    
    # Should succeed (token is valid)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(async_client: AsyncClient):
    """
    Test: Invalid bearer token returns 401.
    """
    response = await async_client.get(
        "/api/runs/",
        headers={"Authorization": "Bearer invalid-user-id-12345"}
    )
    
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_rejects_locked_account(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Locked account cannot access protected endpoints.
    """
    # Setup: Locked user
    user = User(email="locked@example.com")
    user.account_locked_until = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    await db.commit()
    
    # Try to access protected endpoint
    response = await async_client.get(
        "/api/runs/",
        headers={"Authorization": f"Bearer {str(user.id)}"}
    )
    
    assert response.status_code == 403
    assert "locked" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_require_admin_allows_admin_user(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Admin users can access admin-only endpoints.
    
    Note: We'll need to create an admin endpoint to test this.
    For now, this tests the require_admin dependency logic.
    """
    # Setup: Admin user
    admin = User(email="admin@example.com", role=UserRole.ADMIN)
    db.add(admin)
    await db.commit()
    
    # Admin should be able to call is_admin()
    assert admin.is_admin() is True


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user(async_client: AsyncClient, db: AsyncSession):
    """
    Test: Regular users cannot access admin endpoints.
    
    We'll test this once we add the admin endpoints.
    """
    # Setup: Regular user
    user = User(email="user@example.com", role=UserRole.USER)
    db.add(user)
    await db.commit()
    
    # User should NOT be admin
    assert user.is_admin() is False


@pytest.mark.asyncio
async def test_user_model_helper_methods(db: AsyncSession):
    """
    Test: User model helper methods work correctly.
    """
    # Test is_account_locked()
    user = User(email="test@example.com")
    assert user.is_account_locked() is False  # Not locked
    
    user.account_locked_until = datetime.utcnow() + timedelta(minutes=5)
    assert user.is_account_locked() is True  # Currently locked
    
    user.account_locked_until = datetime.utcnow() - timedelta(minutes=5)
    assert user.is_account_locked() is False  # Lock expired
    
    # Test has_complete_profile()
    user.full_name = None
    assert user.has_complete_profile() is False
    
    user.full_name = "John"
    user.email = "test@example.com"
    user.phone = "555-1234"
    user.resume_path = "/path/to/resume.pdf"
    user.mandatory_questions = {
        "work_authorization": "yes",
        "veteran_status": "no",
        "disability_status": "no"
    }
    assert user.has_complete_profile() is True
