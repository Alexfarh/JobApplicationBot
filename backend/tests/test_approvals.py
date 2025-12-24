"""
Tests for the Approvals API.

Tests cover:
- Creating approval requests
- Retrieving approval requests
- Approving applications
- Rejecting applications
- Expiration handling
- Error cases
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.application_run import ApplicationRun
from app.models.job_posting import JobPosting
from app.models.application_task import ApplicationTask, TaskState
from app.models.approval_request import ApprovalRequest


# ============================================================
# CREATE APPROVAL REQUEST TESTS
# ============================================================

@pytest.mark.asyncio
async def test_create_approval_request(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test creating an approval request for a task."""
    # Create run, job, and task in PENDING_APPROVAL state
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    job = JobPosting(
        job_url="https://example.com/job/1",
        apply_url="https://example.com/apply/1"
    )
    db.add(job)
    await db.commit()
    await db.refresh(run)
    await db.refresh(job)
    
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state=TaskState.PENDING_APPROVAL.value
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Create approval request
    response = await client.post(
        "/api/approvals/",
        json={
            "task_id": str(task.id),
            "form_data": [
                {"label": "Company", "value": "Example Corp", "field_type": "text"},
                {"label": "Position", "value": "Software Engineer", "field_type": "text"}
            ],
            "preview_url": "https://example.com/preview",
            "ttl_minutes": 20
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["task_id"] == str(task.id)
    assert data["user_id"] == str(test_user.id)
    assert data["status"] == "pending"
    assert len(data["form_data"]) == 2
    assert data["preview_url"] == "https://example.com/preview"
    assert data["approved_at"] is None
    
    # Verify expires_at is ~20 minutes from now
    expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
    expected_expiry = datetime.utcnow() + timedelta(minutes=20)
    assert abs((expires_at - expected_expiry).total_seconds()) < 10


@pytest.mark.asyncio
async def test_create_approval_request_returns_existing_pending(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that creating approval for same task returns existing pending request."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    job = JobPosting(job_url="https://example.com/job/1", apply_url="https://example.com/apply/1")
    db.add(job)
    await db.commit()
    await db.refresh(run)
    await db.refresh(job)
    
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state=TaskState.PENDING_APPROVAL.value
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Create first approval request
    response1 = await client.post(
        "/api/approvals/",
        json={
            "task_id": str(task.id),
            "form_data": [{"label": "Test", "value": "Data", "field_type": "text"}]
        }
    )
    assert response1.status_code == 201
    approval_id = response1.json()["id"]
    
    # Try to create another approval for same task
    response2 = await client.post(
        "/api/approvals/",
        json={
            "task_id": str(task.id),
            "form_data": [{"label": "Different", "value": "Data", "field_type": "text"}]
        }
    )
    
    # Should return the same approval request
    assert response2.status_code == 201
    assert response2.json()["id"] == approval_id


@pytest.mark.asyncio
async def test_create_approval_task_not_found(
    client: AsyncClient,
    test_user: User
):
    """Test creating approval for non-existent task returns 404."""
    response = await client.post(
        "/api/approvals/",
        json={
            "task_id": "00000000-0000-0000-0000-000000000000",
            "form_data": []
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_approval_wrong_state(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test creating approval for task not in PENDING_APPROVAL state returns 409."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    job = JobPosting(job_url="https://example.com/job/1", apply_url="https://example.com/apply/1")
    db.add(job)
    await db.commit()
    await db.refresh(run)
    await db.refresh(job)
    
    # Task in QUEUED state
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state=TaskState.QUEUED.value
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.post(
        "/api/approvals/",
        json={
            "task_id": str(task.id),
            "form_data": []
        }
    )
    
    assert response.status_code == 409
    assert "PENDING_APPROVAL" in response.json()["detail"]


# ============================================================
# GET APPROVAL REQUEST TESTS
# ============================================================

@pytest.mark.asyncio
async def test_get_approval_request(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test retrieving an approval request."""
    # Create approval request directly
    approval = ApprovalRequest(
        task_id="00000000-0000-0000-0000-000000000001",
        user_id=str(test_user.id),
        form_data=[{"label": "Company", "value": "Test Corp"}],
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=20)
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    response = await client.get(f"/api/approvals/{approval.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(approval.id)
    assert data["user_id"] == str(test_user.id)
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_approval_not_found(client: AsyncClient, test_user: User):
    """Test retrieving non-existent approval returns 404."""
    response = await client.get("/api/approvals/00000000-0000-0000-0000-000000000000")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_approval_wrong_user(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that users can only access their own approvals."""
    # Create approval for different user
    other_user = User(email="other@example.com")
    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)
    
    approval = ApprovalRequest(
        task_id="00000000-0000-0000-0000-000000000001",
        user_id=str(other_user.id),
        form_data=[],
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=20)
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    # test_user tries to access other_user's approval
    response = await client.get(f"/api/approvals/{approval.id}")
    
    assert response.status_code == 404


# ============================================================
# APPROVE/REJECT TESTS
# ============================================================

@pytest.mark.asyncio
async def test_approve_application(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test approving an application."""
    # Create run, job, and task
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    job = JobPosting(job_url="https://example.com/job/1", apply_url="https://example.com/apply/1")
    db.add(job)
    await db.commit()
    await db.refresh(run)
    await db.refresh(job)
    
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state=TaskState.PENDING_APPROVAL.value
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Create approval request
    approval = ApprovalRequest(
        task_id=str(task.id),
        user_id=str(test_user.id),
        form_data=[],
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=20)
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    # Approve
    response = await client.post(
        f"/api/approvals/{approval.id}/approve",
        json={"approved": True, "notes": "Looks good"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["approved_at"] is not None
    
    # Verify task transitioned to APPROVED
    await db.refresh(task)
    assert task.state == TaskState.APPROVED.value


@pytest.mark.asyncio
async def test_reject_application(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test rejecting an application."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    job = JobPosting(job_url="https://example.com/job/1", apply_url="https://example.com/apply/1")
    db.add(job)
    await db.commit()
    await db.refresh(run)
    await db.refresh(job)
    
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state=TaskState.PENDING_APPROVAL.value
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    approval = ApprovalRequest(
        task_id=str(task.id),
        user_id=str(test_user.id),
        form_data=[],
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=20)
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    # Reject
    response = await client.post(
        f"/api/approvals/{approval.id}/approve",
        json={"approved": False}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["approved_at"] is None
    
    # Task should transition to REJECTED (user explicitly declined to submit)
    await db.refresh(task)
    assert task.state == TaskState.REJECTED.value


@pytest.mark.asyncio
async def test_approve_expired_request(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that approving an expired request returns 409 and transitions task to EXPIRED."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    job = JobPosting(job_url="https://example.com/job/1", apply_url="https://example.com/apply/1")
    db.add(job)
    await db.commit()
    await db.refresh(run)
    await db.refresh(job)
    
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state=TaskState.PENDING_APPROVAL.value
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Create approval with expiry in the past
    approval = ApprovalRequest(
        task_id=str(task.id),
        user_id=str(test_user.id),
        form_data=[],
        status="pending",
        expires_at=datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    # Try to approve
    response = await client.post(
        f"/api/approvals/{approval.id}/approve",
        json={"approved": True}
    )
    
    assert response.status_code == 409
    assert "expired" in response.json()["detail"].lower()
    
    # Verify approval marked as expired
    await db.refresh(approval)
    assert approval.status == "expired"
    
    # Verify task transitioned to EXPIRED
    await db.refresh(task)
    assert task.state == TaskState.EXPIRED.value


@pytest.mark.asyncio
async def test_approve_already_approved(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that approving an already-approved request returns 409."""
    approval = ApprovalRequest(
        task_id="00000000-0000-0000-0000-000000000001",
        user_id=str(test_user.id),
        form_data=[],
        status="approved",  # Already approved
        expires_at=datetime.utcnow() + timedelta(minutes=20),
        approved_at=datetime.utcnow()
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    response = await client.post(
        f"/api/approvals/{approval.id}/approve",
        json={"approved": True}
    )
    
    assert response.status_code == 409
    assert "already approved" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_approve_not_found(client: AsyncClient, test_user: User):
    """Test approving non-existent approval returns 404."""
    response = await client.post(
        "/api/approvals/00000000-0000-0000-0000-000000000000/approve",
        json={"approved": True}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_wrong_user(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that users can only approve their own requests."""
    # Create approval for different user
    other_user = User(email="other@example.com")
    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)
    
    approval = ApprovalRequest(
        task_id="00000000-0000-0000-0000-000000000001",
        user_id=str(other_user.id),
        form_data=[],
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=20)
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    # test_user tries to approve other_user's request
    response = await client.post(
        f"/api/approvals/{approval.id}/approve",
        json={"approved": True}
    )
    
    assert response.status_code == 404


# ============================================================
# EDGE CASES AND VALIDATION
# ============================================================

@pytest.mark.asyncio
async def test_create_approval_custom_ttl(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test creating approval with custom TTL."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    job = JobPosting(job_url="https://example.com/job/1", apply_url="https://example.com/apply/1")
    db.add(job)
    await db.commit()
    await db.refresh(run)
    await db.refresh(job)
    
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state=TaskState.PENDING_APPROVAL.value
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Custom TTL of 30 minutes
    response = await client.post(
        "/api/approvals/",
        json={
            "task_id": str(task.id),
            "form_data": [],
            "ttl_minutes": 30
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify expires_at is ~30 minutes from now
    expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
    expected_expiry = datetime.utcnow() + timedelta(minutes=30)
    assert abs((expires_at - expected_expiry).total_seconds()) < 10


@pytest.mark.asyncio
async def test_approval_response_structure(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that approval response contains all expected fields."""
    approval = ApprovalRequest(
        task_id="00000000-0000-0000-0000-000000000001",
        user_id=str(test_user.id),
        form_data=[
            {"label": "Company", "value": "Test Corp", "field_type": "text"},
            {"label": "Position", "value": "Engineer", "field_type": "text"}
        ],
        preview_url="https://example.com/preview",
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=20)
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    response = await client.get(f"/api/approvals/{approval.id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check all required fields
    assert "id" in data
    assert "task_id" in data
    assert "user_id" in data
    assert "form_data" in data
    assert "preview_url" in data
    assert "status" in data
    assert "expires_at" in data
    assert "created_at" in data
    assert "approved_at" in data
    
    # Verify form_data structure
    assert len(data["form_data"]) == 2
    assert data["form_data"][0]["label"] == "Company"
    assert data["form_data"][0]["value"] == "Test Corp"
