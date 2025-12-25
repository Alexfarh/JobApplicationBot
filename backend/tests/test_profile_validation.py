"""
Tests for profile validation on run creation.

Verifies that users cannot create runs without a complete profile.
"""
import io
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User


@pytest_asyncio.fixture
async def incomplete_profile_user(async_client: AsyncClient, db):
    """Create user with incomplete profile and return auth headers."""
    # Request magic link
    response = await async_client.post(
        "/api/auth/request-magic-link",
        json={"email": "incomplete@example.com"}
    )
    assert response.status_code == 200

    # Get token
    result = await db.execute(
        select(User).where(User.email == "incomplete@example.com")
    )
    user = result.scalar_one()
    token = user.magic_link_token

    # Verify token
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": token}
    )
    access_token = response.json()["access_token"]

    return {"Authorization": f"Bearer {access_token}"}

@pytest_asyncio.fixture
async def complete_profile_user(async_client: AsyncClient, db):
    """Create user with complete profile and return auth headers."""
    # Request magic link
    response = await async_client.post(
        "/api/auth/request-magic-link",
        json={"email": "complete@example.com"}
    )
    assert response.status_code == 200

    # Get token
    result = await db.execute(
        select(User).where(User.email == "complete@example.com")
    )
    user = result.scalar_one()
    token = user.magic_link_token

    # Verify token
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": token}
    )
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Complete profile
    await async_client.put(
        "/api/profile",
        headers=headers,
        json={
            "full_name": "Complete User",
            "phone": "+1-555-0199"
        }
    )

    # Set mandatory questions (all critical questions required)
    await async_client.put(
        "/api/profile/questions",
        headers=headers,
        json={
            "work_authorization": "yes",
            "veteran_status": "no",
            "disability_status": "no",
            "gender": "prefer not to say",
            "ethnicity": "prefer not to say"
        }
    )

    # Upload resume
    files = {
        "file": ("resume.pdf", io.BytesIO(b"%PDF-1.4\ntest"), "application/pdf")
    }
    await async_client.post(
        "/api/profile/resume",
        headers=headers,
        files=files
    )

    return headers
# Profile validation tests
@pytest.mark.asyncio
async def test_create_run_requires_complete_profile(async_client: AsyncClient, incomplete_profile_user):
    """Test creating run with incomplete profile returns 403."""
    response = await async_client.post(
        "/api/runs/",
        headers=incomplete_profile_user,
        json={"name": "Test Run", "description": "Should fail"}
    )
    
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "missing_fields" in data["detail"]
    assert "profile_url" in data["detail"]
    assert len(data["detail"]["missing_fields"]) > 0


@pytest.mark.asyncio
async def test_create_run_with_complete_profile_succeeds(async_client: AsyncClient, complete_profile_user):
    """Test creating run with complete profile succeeds."""
    response = await async_client.post(
        "/api/runs/",
        headers=complete_profile_user,
        json={"name": "Test Run", "description": "Should succeed"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Run"
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_profile_validation_checks_all_required_fields(async_client: AsyncClient, incomplete_profile_user):
    """Test validation identifies all missing required fields."""
    response = await async_client.post(
        "/api/runs/",
        headers=incomplete_profile_user,
        json={"name": "Test Run"}
    )
    
    assert response.status_code == 403
    missing_fields = response.json()["detail"]["missing_fields"]
    
    # Should include these required fields
    assert "full name" in missing_fields
    assert "phone number" in missing_fields
    assert "mandatory questions" in missing_fields
    assert "resume" in missing_fields


@pytest.mark.asyncio
async def test_partial_profile_still_fails(async_client: AsyncClient, incomplete_profile_user):
    """Test that partial profile completion still prevents run creation."""
    # Update only some fields
    await async_client.put(
        "/api/profile",
        headers=incomplete_profile_user,
        json={
            "full_name": "Partial User",
            "phone": "+1-555-0123"
        }
    )
    
    # Try to create run
    response = await async_client.post(
        "/api/runs/",
        headers=incomplete_profile_user,
        json={"name": "Test Run"}
    )
    
    assert response.status_code == 403
    missing_fields = response.json()["detail"]["missing_fields"]
    
    # Should still have missing fields (mandatory questions, resume)
    assert len(missing_fields) > 0
    assert "mandatory questions" in missing_fields
    assert "resume" in missing_fields


@pytest.mark.asyncio
async def test_profile_validation_allows_run_after_completion(async_client: AsyncClient, incomplete_profile_user):
    """Test that completing profile allows run creation."""
    # Initially should fail
    response = await async_client.post(
        "/api/runs/",
        headers=incomplete_profile_user,
        json={"name": "Test Run"}
    )
    assert response.status_code == 403
    
    # Complete profile
    await async_client.put(
        "/api/profile",
        headers=incomplete_profile_user,
        json={
            "full_name": "Now Complete",
            "phone": "+1-555-0199"
        }
    )
    
    # Set mandatory questions (all critical questions required)
    await async_client.put(
        "/api/profile/questions",
        headers=incomplete_profile_user,
        json={
            "work_authorization": "yes",
            "veteran_status": "no",
            "disability_status": "no"
        }
    )
    
    # Upload resume
    files = {
        "file": ("resume.pdf", io.BytesIO(b"%PDF-1.4\ntest"), "application/pdf")
    }
    await async_client.post(
        "/api/profile/resume",
        headers=incomplete_profile_user,
        files=files
    )
    
    # Now should succeed
    response = await async_client.post(
        "/api/runs/",
        headers=incomplete_profile_user,
        json={"name": "Test Run", "description": "Should work now"}
    )
    
    assert response.status_code == 201
    assert response.json()["name"] == "Test Run"


@pytest.mark.asyncio
async def test_other_endpoints_dont_require_complete_profile(async_client: AsyncClient, incomplete_profile_user):
    """Test that other endpoints (list, get) don't require complete profile."""
    # List runs should work
    response = await async_client.get(
        "/api/runs/",
        headers=incomplete_profile_user
    )
    assert response.status_code == 200
    
    # Profile endpoints should work
    response = await async_client.get(
        "/api/profile",
        headers=incomplete_profile_user
    )
    assert response.status_code == 200
