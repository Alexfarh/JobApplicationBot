"""
Tests for profile management endpoints.

Tests:
- GET /api/profile (retrieve profile)
- PUT /api/profile (update personal info)
- PUT /api/profile/questions (update mandatory questions)
- PUT /api/profile/preferences (update automation preferences)
- POST /api/profile/resume (upload resume)
- GET /api/profile/resume (download resume)
- DELETE /api/profile/resume (delete resume)
"""
import io
import os
import pytest
import pytest_asyncio
from datetime import datetime
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User
from app.main import app


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, db):
    """
    Create a test user and return auth headers with Bearer token.
    """
    # Request magic link
    response = await async_client.post(
        "/api/auth/request-magic-link",
        json={"email": "profile-test@example.com"}
    )
    assert response.status_code == 200

    # Get user and token
    result = await db.execute(
        select(User).where(User.email == "profile-test@example.com")
    )
    user = result.scalar_one()
    token = user.magic_link_token

    # Verify token to get Bearer token
    response = await async_client.post(
        "/api/auth/verify-token",
        json={"token": token}
    )
    assert response.status_code == 200
    data = response.json()
    access_token = data["access_token"]

    return {"Authorization": f"Bearer {access_token}"}
# GET /api/profile tests
@pytest.mark.asyncio
async def test_get_profile_success(async_client: AsyncClient, auth_headers):
    """Test retrieving profile returns user data."""
    response = await async_client.get("/api/profile", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile-test@example.com"
    assert data["role"] == "user"
    assert data["profile_complete"] is False  # No required fields filled
    assert data["resume_uploaded"] is False
    assert "user_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_profile_requires_auth(async_client: AsyncClient):
    """Test getting profile without auth returns 422 (missing required header)."""
    response = await async_client.get("/api/profile")
    assert response.status_code == 422  # FastAPI validates required headers before auth


# PUT /api/profile tests
@pytest.mark.asyncio
async def test_update_profile_personal_info(async_client: AsyncClient, auth_headers):
    """Test updating personal information."""
    profile_data = {
        "full_name": "John Doe",
        "phone": "+1-555-0123",
        "address_street": "123 Main St",
        "address_city": "San Francisco",
        "address_state": "CA",
        "address_zip": "94105",
        "address_country": "USA"
    }
    
    response = await async_client.put(
        "/api/profile",
        headers=auth_headers,
        json=profile_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "John Doe"
    assert data["phone"] == "+1-555-0123"
    assert data["address_city"] == "San Francisco"
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_update_profile_professional_urls(async_client: AsyncClient, auth_headers):
    """Test updating professional URLs."""
    profile_data = {
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "github_url": "https://github.com/johndoe",
        "portfolio_url": "https://johndoe.dev"
    }
    
    response = await async_client.put(
        "/api/profile",
        headers=auth_headers,
        json=profile_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["linkedin_url"] == "https://linkedin.com/in/johndoe"
    assert data["github_url"] == "https://github.com/johndoe"
    assert data["portfolio_url"] == "https://johndoe.dev/"


@pytest.mark.asyncio
async def test_update_profile_partial_update(async_client: AsyncClient, auth_headers):
    """Test partial update only changes provided fields."""
    # First update
    await async_client.put(
        "/api/profile",
        headers=auth_headers,
        json={"full_name": "John Doe", "phone": "+1-555-0123"}
    )
    
    # Second update (only name)
    response = await async_client.put(
        "/api/profile",
        headers=auth_headers,
        json={"full_name": "Jane Doe"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Jane Doe"
    assert data["phone"] == "+1-555-0123"  # Phone unchanged


@pytest.mark.asyncio
async def test_update_profile_requires_auth(async_client: AsyncClient):
    """Test updating profile without auth returns 422 (missing required header)."""
    response = await async_client.put(
        "/api/profile",
        json={"full_name": "John Doe"}
    )
    assert response.status_code == 422  # FastAPI validates required headers before auth


# PUT /api/profile/questions tests
@pytest.mark.asyncio
async def test_update_mandatory_questions(async_client: AsyncClient, auth_headers):
    """Test updating mandatory questions."""
    questions = {
        "work_authorization": "US Citizen",
        "veteran_status": "no",
        "disability_status": "prefer_not_to_say",
        "salary_min": 100000,
        "salary_max": 150000,
        "salary_currency": "USD"
    }
    
    response = await async_client.put(
        "/api/profile/questions",
        headers=auth_headers,
        json=questions
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["mandatory_questions"]["work_authorization"] == "US Citizen"
    assert data["mandatory_questions"]["salary_min"] == 100000


@pytest.mark.asyncio
async def test_update_mandatory_questions_merges_with_existing(async_client: AsyncClient, auth_headers):
    """Test updating questions merges with existing data."""
    # First update
    await async_client.put(
        "/api/profile/questions",
        headers=auth_headers,
        json={"work_authorization": "US Citizen", "veteran_status": "no"}
    )
    
    # Second update (different fields)
    response = await async_client.put(
        "/api/profile/questions",
        headers=auth_headers,
        json={"salary_min": 120000, "salary_max": 180000}
    )
    
    assert response.status_code == 200
    data = response.json()
    # Both old and new fields should be present
    assert data["mandatory_questions"]["work_authorization"] == "US Citizen"
    assert data["mandatory_questions"]["salary_min"] == 120000


# PUT /api/profile/preferences tests
@pytest.mark.asyncio
async def test_update_preferences(async_client: AsyncClient, auth_headers):
    """Test updating automation preferences."""
    preferences = {
        "optimistic_mode": False,
        "require_approval": True,
        "preferred_platforms": ["greenhouse", "lever"]
    }
    
    response = await async_client.put(
        "/api/profile/preferences",
        headers=auth_headers,
        json=preferences
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["preferences"]["optimistic_mode"] is False
    assert data["preferences"]["require_approval"] is True
    assert "greenhouse" in data["preferences"]["preferred_platforms"]


@pytest.mark.asyncio
async def test_update_preferences_has_defaults(async_client: AsyncClient, auth_headers):
    """Test preferences are initialized with defaults if None."""
    # Update one preference
    response = await async_client.put(
        "/api/profile/preferences",
        headers=auth_headers,
        json={"optimistic_mode": False}
    )
    
    assert response.status_code == 200
    data = response.json()
    # Should have defaults for other fields
    assert "require_approval" in data["preferences"]
    assert "preferred_platforms" in data["preferences"]


# POST /api/profile/resume tests
@pytest.mark.asyncio
async def test_upload_resume_pdf_success(async_client: AsyncClient, auth_headers, db):
    """Test uploading PDF resume."""
    # Create fake PDF file
    pdf_content = b"%PDF-1.4\n%fake pdf content"
    files = {
        "file": ("resume.pdf", io.BytesIO(pdf_content), "application/pdf")
    }
    
    response = await async_client.post(
        "/api/profile/resume",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["resume_uploaded"] is True
    assert data["resume_filename"] == "resume.pdf"
    assert data["resume_uploaded_at"] is not None
    assert data["resume_size_bytes"] > 0
    
    # Verify file exists on disk
    resume_path = Path(data["resume_uploaded_at"])  # This will be wrong, need to check actual path
    # Instead, check that resume_path field is set
    result = await db.execute(
        select(User).where(User.email == "profile-test@example.com")
    )
    user = result.scalar_one()
    assert user.resume_path is not None
    assert Path(user.resume_path).exists()


@pytest.mark.asyncio
async def test_upload_resume_docx_success(async_client: AsyncClient, auth_headers):
    """Test uploading DOCX resume."""
    # Create fake DOCX file
    docx_content = b"PK fake docx content"
    files = {
        "file": ("resume.docx", io.BytesIO(docx_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    }
    
    response = await async_client.post(
        "/api/profile/resume",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["resume_uploaded"] is True
    assert data["resume_filename"] == "resume.docx"


@pytest.mark.asyncio
async def test_upload_resume_invalid_extension(async_client: AsyncClient, auth_headers):
    """Test uploading file with invalid extension returns 400."""
    files = {
        "file": ("resume.txt", io.BytesIO(b"text file"), "text/plain")
    }
    
    response = await async_client.post(
        "/api/profile/resume",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_resume_replaces_old_resume(async_client: AsyncClient, auth_headers, db):
    """Test uploading new resume deletes old one."""
    # Upload first resume
    files1 = {
        "file": ("resume1.pdf", io.BytesIO(b"%PDF-1.4\nfirst"), "application/pdf")
    }
    response1 = await async_client.post(
        "/api/profile/resume",
        headers=auth_headers,
        files=files1
    )
    assert response1.status_code == 200
    
    # Get old resume path
    result = await db.execute(
        select(User).where(User.email == "profile-test@example.com")
    )
    user = result.scalar_one()
    old_resume_path = Path(user.resume_path)
    assert old_resume_path.exists()
    
    # Upload second resume
    files2 = {
        "file": ("resume2.pdf", io.BytesIO(b"%PDF-1.4\nsecond"), "application/pdf")
    }
    response2 = await async_client.post(
        "/api/profile/resume",
        headers=auth_headers,
        files=files2
    )
    assert response2.status_code == 200
    
    # Old resume should be deleted
    assert not old_resume_path.exists()


@pytest.mark.asyncio
async def test_upload_resume_requires_auth(async_client: AsyncClient):
    """Test uploading resume without auth returns 422 (missing required header)."""
    files = {
        "file": ("resume.pdf", io.BytesIO(b"%PDF-1.4\ntest"), "application/pdf")
    }
    response = await async_client.post("/api/profile/resume", files=files)
    assert response.status_code == 422  # FastAPI validates required headers before auth


# GET /api/profile/resume tests
@pytest.mark.asyncio
async def test_download_resume_success(async_client: AsyncClient, auth_headers):
    """Test downloading resume returns file."""
    # First upload a resume
    files = {
        "file": ("test_resume.pdf", io.BytesIO(b"%PDF-1.4\ntest content"), "application/pdf")
    }
    await async_client.post(
        "/api/profile/resume",
        headers=auth_headers,
        files=files
    )
    
    # Download resume
    response = await async_client.get(
        "/api/profile/resume",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert b"PDF" in response.content


@pytest.mark.asyncio
async def test_download_resume_not_found(async_client: AsyncClient, auth_headers):
    """Test downloading resume when none uploaded returns 404."""
    response = await async_client.get(
        "/api/profile/resume",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "No resume uploaded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_download_resume_requires_auth(async_client: AsyncClient):
    """Test downloading resume without auth returns 422 (missing required header)."""
    response = await async_client.get("/api/profile/resume")
    assert response.status_code == 422  # FastAPI validates required headers before auth


# DELETE /api/profile/resume tests
@pytest.mark.asyncio
async def test_delete_resume_success(async_client: AsyncClient, auth_headers, db):
    """Test deleting resume removes file and updates record."""
    # Upload resume first
    files = {
        "file": ("resume.pdf", io.BytesIO(b"%PDF-1.4\ntest"), "application/pdf")
    }
    await async_client.post(
        "/api/profile/resume",
        headers=auth_headers,
        files=files
    )
    
    # Get resume path before deletion
    result = await db.execute(
        select(User).where(User.email == "profile-test@example.com")
    )
    user = result.scalar_one()
    resume_path = Path(user.resume_path)
    assert resume_path.exists()

    # Delete resume
    response = await async_client.delete(
        "/api/profile/resume",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["resume_uploaded"] is False
    assert data["resume_filename"] is None

    # File should be deleted from disk
    assert not resume_path.exists()

    # Database should be updated
    await db.refresh(user)
    assert user.resume_path is None


@pytest.mark.asyncio
async def test_delete_resume_not_found(async_client: AsyncClient, auth_headers):
    """Test deleting resume when none uploaded returns 404."""
    response = await async_client.delete(
        "/api/profile/resume",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "No resume uploaded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_resume_requires_auth(async_client: AsyncClient):
    """Test deleting resume without auth returns 422 (missing required header)."""
    response = await async_client.delete("/api/profile/resume")
    assert response.status_code == 422  # FastAPI validates required headers before auth


# Profile completeness tests
@pytest.mark.asyncio
async def test_profile_complete_status(async_client: AsyncClient, auth_headers):
    """Test profile_complete is True when required fields are filled."""
    # Update all required fields
    await async_client.put(
        "/api/profile",
        headers=auth_headers,
        json={
            "full_name": "John Doe",
            "phone": "+1-555-0123",
            "address_city": "San Francisco",
            "address_state": "CA",
            "address_country": "USA"
        }
    )
    
    # Update mandatory questions
    await async_client.put(
        "/api/profile/questions",
        headers=auth_headers,
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
        headers=auth_headers,
        files=files
    )
    
    # Check profile completeness
    response = await async_client.get("/api/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["profile_complete"] is True
