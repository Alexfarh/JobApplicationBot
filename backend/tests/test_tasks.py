"""
Tests for Tasks API endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application_task import ApplicationTask
from app.models.application_run import ApplicationRun
from app.models.job_posting import JobPosting
from app.models.user import User


# Helper to create unique jobs
async def create_job(db: AsyncSession, index: int = 1) -> JobPosting:
    """Create a unique job posting for testing."""
    job = JobPosting(
        job_url=f"https://example.com/job/{index}",
        apply_url=f"https://example.com/apply/{index}"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


# ============================================================
# LIST TASKS TESTS
# ============================================================

@pytest.mark.asyncio
async def test_list_tasks_empty(client: AsyncClient, test_user: User):
    """Test listing tasks when none exist."""
    response = await client.get("/api/tasks/")
    
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test listing all tasks."""
    # Create run
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create tasks with different jobs (UNIQUE constraint on run_id+job_id)
    job1 = await create_job(db, 1)
    job2 = await create_job(db, 2)
    
    tasks = [
        ApplicationTask(
            run_id=str(run.id),
            job_id=job1.id,
            state="QUEUED",
            priority=50
        ),
        ApplicationTask(
            run_id=str(run.id),
            job_id=job2.id,
            state="RUNNING",
            priority=50
        ),
    ]
    db.add_all(tasks)
    await db.commit()
    
    response = await client.get("/api/tasks/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_tasks_filter_by_run_id(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test filtering tasks by run_id."""
    # Create two runs
    run1 = ApplicationRun(user_id=str(test_user.id), status="running")
    run2 = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add_all([run1, run2])
    
    job = JobPosting(
        job_url="https://example.com/job/1",
        apply_url="https://example.com/apply/1"
    )
    db.add(job)
    await db.commit()
    await db.refresh(run1)
    await db.refresh(run2)
    await db.refresh(job)
    
    # Create tasks for both runs
    task1 = ApplicationTask(run_id=str(run1.id), job_id=job.id, state="QUEUED")
    task2 = ApplicationTask(run_id=str(run2.id), job_id=job.id, state="QUEUED")
    db.add_all([task1, task2])
    await db.commit()
    
    # Filter by run1
    response = await client.get(f"/api/tasks/?run_id={run1.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == str(run1.id)


@pytest.mark.asyncio
async def test_list_tasks_filter_by_state(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test filtering tasks by state."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create tasks with different states (need different jobs for UNIQUE constraint)
    job1 = await create_job(db, 1)
    job2 = await create_job(db, 2)
    job3 = await create_job(db, 3)
    
    tasks = [
        ApplicationTask(run_id=str(run.id), job_id=job1.id, state="QUEUED"),
        ApplicationTask(run_id=str(run.id), job_id=job2.id, state="FAILED"),
        ApplicationTask(run_id=str(run.id), job_id=job3.id, state="QUEUED"),
    ]
    db.add_all(tasks)
    await db.commit()
    
    # Filter by QUEUED
    response = await client.get("/api/tasks/?state=QUEUED")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(t["state"] == "QUEUED" for t in data)
    
    # Filter by FAILED
    response = await client.get("/api/tasks/?state=FAILED")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["state"] == "FAILED"


@pytest.mark.asyncio
async def test_list_tasks_filter_by_job_id(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test filtering tasks by job_id."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    
    # Create two jobs
    job1 = JobPosting(
        job_url="https://example.com/job/1",
        apply_url="https://example.com/apply/1"
    )
    job2 = JobPosting(
        job_url="https://example.com/job/2",
        apply_url="https://example.com/apply/2"
    )
    db.add_all([job1, job2])
    await db.commit()
    await db.refresh(run)
    await db.refresh(job1)
    await db.refresh(job2)
    
    # Create tasks for both jobs
    task1 = ApplicationTask(run_id=str(run.id), job_id=job1.id, state="QUEUED")
    task2 = ApplicationTask(run_id=str(run.id), job_id=job2.id, state="QUEUED")
    db.add_all([task1, task2])
    await db.commit()
    
    # Filter by job1
    response = await client.get(f"/api/tasks/?job_id={job1.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["job_id"] == job1.id


@pytest.mark.asyncio
async def test_list_tasks_multiple_filters_combined(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test combining multiple filters (run_id + state + job_id)."""
    run1 = ApplicationRun(user_id=str(test_user.id), status="running")
    run2 = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add_all([run1, run2])
    
    job1 = JobPosting(
        job_url="https://example.com/job/1",
        apply_url="https://example.com/apply/1"
    )
    job2 = JobPosting(
        job_url="https://example.com/job/2",
        apply_url="https://example.com/apply/2"
    )
    db.add_all([job1, job2])
    await db.commit()
    await db.refresh(run1)
    await db.refresh(run2)
    await db.refresh(job1)
    await db.refresh(job2)
    
    # Create tasks with different combinations (need different jobs for UNIQUE constraint)
    job3 = JobPosting(job_url="https://example.com/job/3", apply_url="https://example.com/apply/3")
    db.add(job3)
    await db.commit()
    await db.refresh(job3)
    
    tasks = [
        ApplicationTask(run_id=str(run1.id), job_id=job1.id, state="QUEUED"),
        ApplicationTask(run_id=str(run1.id), job_id=job3.id, state="FAILED"),  # Different job for same run
        ApplicationTask(run_id=str(run1.id), job_id=job2.id, state="QUEUED"),
        ApplicationTask(run_id=str(run2.id), job_id=job1.id, state="QUEUED"),
    ]
    db.add_all(tasks)
    await db.commit()
    
    # Filter: run1 + job1 + QUEUED
    response = await client.get(
        f"/api/tasks/?run_id={run1.id}&job_id={job1.id}&state=QUEUED"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == str(run1.id)
    assert data[0]["job_id"] == job1.id
    assert data[0]["state"] == "QUEUED"


@pytest.mark.asyncio
async def test_list_tasks_ordered_by_priority_and_time(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that tasks are ordered by priority DESC, queued_at ASC."""
    from datetime import datetime, timedelta
    
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create tasks with different priorities and times (need different jobs)
    base_time = datetime.utcnow()
    job1 = await create_job(db, 1)
    job2 = await create_job(db, 2)
    job3 = await create_job(db, 3)
    
    tasks = [
        ApplicationTask(
            run_id=str(run.id),
            job_id=job1.id,
            state="QUEUED",
            priority=50,
            queued_at=base_time + timedelta(seconds=2)
        ),
        ApplicationTask(
            run_id=str(run.id),
            job_id=job2.id,
            state="QUEUED",
            priority=100,  # Highest priority
            queued_at=base_time + timedelta(seconds=1)
        ),
        ApplicationTask(
            run_id=str(run.id),
            job_id=job3.id,
            state="QUEUED",
            priority=50,
            queued_at=base_time  # Oldest with priority=50
        ),
    ]
    db.add_all(tasks)
    await db.commit()
    task_ids = [t.id for t in tasks]
    
    response = await client.get("/api/tasks/")
    assert response.status_code == 200
    data = response.json()
    
    # Expected order: priority=100 first, then priority=50 (oldest first)
    assert data[0]["id"] == str(task_ids[1])  # priority=100
    assert data[1]["id"] == str(task_ids[2])  # priority=50, oldest
    assert data[2]["id"] == str(task_ids[0])  # priority=50, newest


@pytest.mark.asyncio
async def test_list_tasks_pagination(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test pagination with skip and limit."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create 10 tasks with different jobs
    for i in range(10):
        job = await create_job(db, i + 1)
        task = ApplicationTask(run_id=str(run.id), job_id=job.id, state="QUEUED")
        db.add(task)
    await db.commit()
    
    # Get first 3
    response = await client.get("/api/tasks/?skip=0&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    # Get next 3
    response = await client.get("/api/tasks/?skip=3&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    # Get last 4
    response = await client.get("/api/tasks/?skip=6&limit=10")
    assert response.status_code == 200
    assert len(response.json()) == 4


# ============================================================
# GET SINGLE TASK TESTS
# ============================================================

@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test getting a specific task by ID."""
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
    
    task = ApplicationTask(run_id=str(run.id), job_id=job.id, state="QUEUED")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.get(f"/api/tasks/{task.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(task.id)
    assert data["state"] == "QUEUED"
    assert data["priority"] == 50


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient, test_user: User):
    """Test getting a non-existent task."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/tasks/{fake_uuid}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================
# RESUME TASK TESTS
# ============================================================

@pytest.mark.asyncio
async def test_resume_failed_task(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test resuming a FAILED task."""
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
        state="FAILED",
        priority=50,
        last_error_message="Timeout"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    task_id = task.id
    
    response = await client.post(f"/api/tasks/{task_id}/resume")
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == str(task_id)
    assert data["old_state"] == "FAILED"
    assert data["new_state"] == "QUEUED"
    assert data["priority"] == 100  # Priority boost
    
    # Verify task state changed in DB
    await db.refresh(task)
    assert task.state == "QUEUED"
    assert task.priority == 100


@pytest.mark.asyncio
async def test_resume_needs_auth_task(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test resuming a NEEDS_AUTH task."""
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
        state="NEEDS_AUTH",
        priority=50
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.post(f"/api/tasks/{task.id}/resume")
    
    assert response.status_code == 200
    data = response.json()
    assert data["old_state"] == "NEEDS_AUTH"
    assert data["new_state"] == "QUEUED"
    assert data["priority"] == 100


@pytest.mark.asyncio
async def test_resume_needs_user_task(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test resuming a NEEDS_USER task."""
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
        state="NEEDS_USER",
        priority=50
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.post(f"/api/tasks/{task.id}/resume")
    
    assert response.status_code == 200
    assert response.json()["old_state"] == "NEEDS_USER"
    assert response.json()["new_state"] == "QUEUED"


@pytest.mark.asyncio
async def test_resume_expired_task(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test resuming an EXPIRED task."""
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
        state="EXPIRED",
        priority=50
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.post(f"/api/tasks/{task.id}/resume")
    
    assert response.status_code == 200
    assert response.json()["old_state"] == "EXPIRED"
    assert response.json()["new_state"] == "QUEUED"


@pytest.mark.asyncio
async def test_resume_task_invalid_state(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test that resuming a task in non-resumable state is rejected."""
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
    
    # Try to resume SUBMITTED task (not resumable)
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job.id,
        state="SUBMITTED",
        priority=50
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.post(f"/api/tasks/{task.id}/resume")
    
    assert response.status_code == 409
    assert "Cannot resume task in state SUBMITTED" in response.json()["detail"]


@pytest.mark.asyncio
async def test_resume_task_not_found(client: AsyncClient, test_user: User):
    """Test resuming a non-existent task."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/api/tasks/{fake_uuid}/resume")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resume_queued_task_rejected(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test that resuming a QUEUED task is rejected (already ready)."""
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
        state="QUEUED",
        priority=50
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.post(f"/api/tasks/{task.id}/resume")
    
    assert response.status_code == 409
    assert "Cannot resume" in response.json()["detail"]


@pytest.mark.asyncio
async def test_resume_running_task_rejected(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test that resuming a RUNNING task is rejected (currently processing)."""
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
        state="RUNNING",
        priority=50
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.post(f"/api/tasks/{task.id}/resume")
    
    assert response.status_code == 409
    assert "Cannot resume" in response.json()["detail"]


# ============================================================
# EDGE CASES & VALIDATION
# ============================================================

@pytest.mark.asyncio
async def test_list_tasks_pagination_boundaries(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test pagination edge cases."""
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create 5 tasks with different jobs
    for i in range(5):
        job = await create_job(db, i + 1)
        task = ApplicationTask(run_id=str(run.id), job_id=job.id, state="QUEUED")
        db.add(task)
    await db.commit()
    
    # Skip beyond available
    response = await client.get("/api/tasks/?skip=100")
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # Limit at max (100)
    response = await client.get("/api/tasks/?limit=100")
    assert response.status_code == 200
    assert len(response.json()) == 5
    
    # Invalid limit (> 100) should be rejected
    response = await client.get("/api/tasks/?limit=101")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_task_response_structure(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that task response contains all expected fields."""
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
        state="FAILED",
        last_error_code="TIMEOUT",
        last_error_message="Request timed out"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    response = await client.get(f"/api/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    
    # Verify all fields present
    required_fields = [
        "id", "run_id", "job_id", "state", "priority", "attempt_count",
        "last_error_code", "last_error_message", "queued_at",
        "started_at", "last_state_change_at"
    ]
    for field in required_fields:
        assert field in data
    
    # Verify specific values
    assert data["state"] == "FAILED"
    assert data["last_error_code"] == "TIMEOUT"
    assert data["last_error_message"] == "Request timed out"
