"""
Tests for Jobs API endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_posting import JobPosting
from app.models.user import User


# ============================================================
# CREATE JOB TESTS
# ============================================================

@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, test_user: User):
    """Test creating a new job posting."""
    job_data = {
        "job_url": "https://example.com/job/123",
        "apply_url": "https://example.com/apply/123",
        "source": "greenhouse",
        "job_title": "Senior Software Engineer",
        "company_name": "Test Corp",
        "location_text": "San Francisco, CA",
        "work_mode": "remote",
        "employment_type": "full-time",
        "skills": ["Python", "FastAPI", "PostgreSQL"]
    }
    
    response = await client.post("/api/jobs/", json=job_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["job_title"] == "Senior Software Engineer"
    assert data["company_name"] == "Test Corp"
    assert data["has_been_applied_to"] is False
    assert data["skills"] == ["Python", "FastAPI", "PostgreSQL"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_job_duplicate_not_applied_returns_existing(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that duplicate apply_url returns existing job if not yet applied (allows retry)."""
    # Create first job (not applied)
    job = JobPosting(
        job_url="https://example.com/job/123",
        apply_url="https://example.com/apply/123",
        job_title="Software Engineer",
        company_name="Test Corp",
        has_been_applied_to=False
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    existing_id = job.id
    
    # Try to create duplicate
    job_data = {
        "job_url": "https://example.com/job/456",  # Different job URL
        "apply_url": "https://example.com/apply/123",  # Same apply URL
        "job_title": "Different Title"
    }
    
    response = await client.post("/api/jobs/", json=job_data)
    
    # Should return 201 and the existing job (allows retry for FAILED/EXPIRED)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == existing_id
    assert data["job_title"] == "Software Engineer"  # Original title, not new one
    assert data["company_name"] == "Test Corp"
    assert data["has_been_applied_to"] is False


@pytest.mark.asyncio
async def test_create_job_duplicate_already_applied_rejects(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that duplicate apply_url is rejected if already applied (SUBMITTED)."""
    from datetime import datetime
    
    # Create job that's already been applied to
    job = JobPosting(
        job_url="https://example.com/job/123",
        apply_url="https://example.com/apply/123",
        job_title="Software Engineer",
        company_name="Test Corp",
        has_been_applied_to=True,
        last_applied_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    
    # Try to create duplicate
    job_data = {
        "job_url": "https://example.com/job/456",
        "apply_url": "https://example.com/apply/123",
        "job_title": "Different Title"
    }
    
    response = await client.post("/api/jobs/", json=job_data)
    
    # Should reject with 409
    assert response.status_code == 409
    assert "Already applied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_job_minimal_fields(client: AsyncClient, test_user: User):
    """Test creating a job with only required fields."""
    job_data = {
        "job_url": "https://example.com/job/minimal",
        "apply_url": "https://example.com/apply/minimal"
    }
    
    response = await client.post("/api/jobs/", json=job_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["job_url"] == job_data["job_url"]
    assert data["apply_url"] == job_data["apply_url"]
    assert data["job_title"] is None
    assert data["company_name"] is None


@pytest.mark.asyncio
async def test_create_job_with_all_fields(client: AsyncClient, test_user: User):
    """Test creating a job with all optional fields populated."""
    job_data = {
        "job_url": "https://example.com/job/full",
        "apply_url": "https://example.com/apply/full",
        "source": "greenhouse",
        "job_title": "Staff Engineer",
        "company_name": "Acme Corp",
        "location_text": "New York, NY",
        "work_mode": "hybrid",
        "employment_type": "full-time",
        "industry": "fintech",
        "description_raw": "<p>Join our team</p>",
        "description_clean": "Join our team",
        "skills": ["Python", "React", "AWS", "Kubernetes"]
    }
    
    response = await client.post("/api/jobs/", json=job_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["source"] == "greenhouse"
    assert data["job_title"] == "Staff Engineer"
    assert data["industry"] == "fintech"
    assert len(data["skills"]) == 4
    assert "Kubernetes" in data["skills"]


@pytest.mark.asyncio
async def test_create_job_empty_skills_array(client: AsyncClient, test_user: User):
    """Test creating a job with empty skills array."""
    job_data = {
        "job_url": "https://example.com/job/noskills",
        "apply_url": "https://example.com/apply/noskills",
        "skills": []
    }
    
    response = await client.post("/api/jobs/", json=job_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["skills"] == []


@pytest.mark.asyncio
async def test_create_job_unauthenticated_rejected(client: AsyncClient):
    """Test that unauthenticated requests are rejected."""
    # Create a new client without auth headers
    from httpx import AsyncClient as RawClient
    from app.main import app
    
    async with RawClient(app=app, base_url="http://test") as unauth_client:
        job_data = {
            "job_url": "https://example.com/job/unauth",
            "apply_url": "https://example.com/apply/unauth"
        }
        
        response = await unauth_client.post("/api/jobs/", json=job_data)
        # FastAPI returns 422 when required header (Authorization) is missing
        assert response.status_code == 422
        assert response.status_code == 422


# ============================================================
# LIST JOBS TESTS
# ============================================================

@pytest.mark.asyncio
async def test_list_jobs_empty(client: AsyncClient, test_user: User):
    """Test listing jobs when none exist."""
    response = await client.get("/api/jobs/")
    
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test listing all jobs."""
    # Create multiple jobs
    jobs = [
        JobPosting(
            job_url=f"https://example.com/job/{i}",
            apply_url=f"https://example.com/apply/{i}",
            job_title=f"Engineer {i}",
            company_name="Test Corp",
            has_been_applied_to=(i % 2 == 0)
        )
        for i in range(5)
    ]
    db.add_all(jobs)
    await db.commit()
    
    response = await client.get("/api/jobs/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_list_jobs_multiple_filters_combined(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test combining multiple filters (applied + company + source)."""
    jobs = [
        JobPosting(
            job_url="https://example.com/job/1",
            apply_url="https://example.com/apply/1",
            company_name="Google Inc",
            source="greenhouse",
            has_been_applied_to=False
        ),
        JobPosting(
            job_url="https://example.com/job/2",
            apply_url="https://example.com/apply/2",
            company_name="Google Inc",
            source="greenhouse",
            has_been_applied_to=True
        ),
        JobPosting(
            job_url="https://example.com/job/3",
            apply_url="https://example.com/apply/3",
            company_name="Google Inc",
            source="workday",
            has_been_applied_to=False
        ),
    ]
    db.add_all(jobs)
    await db.commit()
    
    # Filter: Google + greenhouse + not applied
    response = await client.get("/api/jobs/?company=Google&source=greenhouse&applied=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["company_name"] == "Google Inc"
    assert data[0]["source"] == "greenhouse"
    assert data[0]["has_been_applied_to"] is False


@pytest.mark.asyncio
async def test_list_jobs_filter_by_work_mode(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test filtering jobs by work_mode."""
    jobs = [
        JobPosting(
            job_url="https://example.com/job/1",
            apply_url="https://example.com/apply/1",
            work_mode="remote"
        ),
        JobPosting(
            job_url="https://example.com/job/2",
            apply_url="https://example.com/apply/2",
            work_mode="hybrid"
        ),
        JobPosting(
            job_url="https://example.com/job/3",
            apply_url="https://example.com/apply/3",
            work_mode="remote"
        ),
    ]
    db.add_all(jobs)
    await db.commit()
    
    response = await client.get("/api/jobs/?work_mode=remote")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(job["work_mode"] == "remote" for job in data)


@pytest.mark.asyncio
async def test_list_jobs_case_insensitive_company_search(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that company name search is case-insensitive."""
    job = JobPosting(
        job_url="https://example.com/job/1",
        apply_url="https://example.com/apply/1",
        company_name="Google Inc"
    )
    db.add(job)
    await db.commit()
    
    # Search with lowercase
    response = await client.get("/api/jobs/?company=google")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # Search with uppercase
    response = await client.get("/api/jobs/?company=GOOGLE")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # Search with mixed case
    response = await client.get("/api/jobs/?company=GoOgLe")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_list_jobs_filter_by_applied(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test filtering jobs by has_been_applied_to."""
    # Create jobs with different applied status
    jobs = [
        JobPosting(
            job_url="https://example.com/job/1",
            apply_url="https://example.com/apply/1",
            has_been_applied_to=True
        ),
        JobPosting(
            job_url="https://example.com/job/2",
            apply_url="https://example.com/apply/2",
            has_been_applied_to=False
        ),
        JobPosting(
            job_url="https://example.com/job/3",
            apply_url="https://example.com/apply/3",
            has_been_applied_to=False
        ),
    ]
    db.add_all(jobs)
    await db.commit()
    
    # Filter for unapplied jobs
    response = await client.get("/api/jobs/?applied=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(not job["has_been_applied_to"] for job in data)
    
    # Filter for applied jobs
    response = await client.get("/api/jobs/?applied=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["has_been_applied_to"] is True


@pytest.mark.asyncio
async def test_list_jobs_filter_by_company(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test filtering jobs by company name (partial match)."""
    jobs = [
        JobPosting(
            job_url="https://example.com/job/1",
            apply_url="https://example.com/apply/1",
            company_name="Google Inc"
        ),
        JobPosting(
            job_url="https://example.com/job/2",
            apply_url="https://example.com/apply/2",
            company_name="Microsoft Corp"
        ),
        JobPosting(
            job_url="https://example.com/job/3",
            apply_url="https://example.com/apply/3",
            company_name="Amazon"
        ),
    ]
    db.add_all(jobs)
    await db.commit()
    
    response = await client.get("/api/jobs/?company=Google")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Google" in data[0]["company_name"]
    
    # Search for partial match "Corp" should match "Microsoft Corp"
    response = await client.get("/api/jobs/?company=Corp")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Microsoft" in data[0]["company_name"]
    
    # Search for "Inc" should match "Google Inc"
    response = await client.get("/api/jobs/?company=Inc")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Google" in data[0]["company_name"]
    
    # Search that matches nothing
    response = await client.get("/api/jobs/?company=NonExistent")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_list_jobs_pagination(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test pagination with skip and limit."""
    # Create 10 jobs
    jobs = [
        JobPosting(
            job_url=f"https://example.com/job/{i}",
            apply_url=f"https://example.com/apply/{i}",
            job_title=f"Job {i}"
        )
        for i in range(10)
    ]
    db.add_all(jobs)
    await db.commit()
    
    # Get first 3
    response = await client.get("/api/jobs/?skip=0&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    # Get next 3
    response = await client.get("/api/jobs/?skip=3&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    # Get last 4
    response = await client.get("/api/jobs/?skip=6&limit=10")
    assert response.status_code == 200
    assert len(response.json()) == 4


# ============================================================
# GET JOB TESTS
# ============================================================

@pytest.mark.asyncio
async def test_get_job(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test getting a specific job by ID."""
    job = JobPosting(
        job_url="https://example.com/job/123",
        apply_url="https://example.com/apply/123",
        job_title="Software Engineer",
        company_name="Test Corp"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    response = await client.get(f"/api/jobs/{job.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job.id
    assert data["job_title"] == "Software Engineer"


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, test_user: User):
    """Test getting a non-existent job."""
    response = await client.get("/api/jobs/99999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================
# DELETE JOB TESTS
# ============================================================

@pytest.mark.asyncio
async def test_delete_job(client: AsyncClient, test_user: User, db: AsyncSession):
    """Test deleting a job."""
    job = JobPosting(
        job_url="https://example.com/job/delete",
        apply_url="https://example.com/apply/delete",
        job_title="To Delete"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    job_id = job.id
    
    response = await client.delete(f"/api/jobs/{job_id}")
    
    assert response.status_code == 204
    
    # Verify job is deleted
    from sqlalchemy import select
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_job_not_found(client: AsyncClient, test_user: User):
    """Test deleting a non-existent job."""
    response = await client.delete("/api/jobs/99999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_job_with_tasks_prevented_by_default(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that deleting a job with tasks is prevented by default (safe mode)."""
    from app.models.application_task import ApplicationTask
    from app.models.application_run import ApplicationRun
    
    # Create a run
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create a job
    job = JobPosting(
        job_url="https://example.com/job/protected",
        apply_url="https://example.com/apply/protected",
        job_title="Protected Job"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    job_id = job.id
    
    # Create a task for this job
    task = ApplicationTask(
        run_id=str(run.id),
        job_id=job_id,
        state="SUBMITTED"
    )
    db.add(task)
    await db.commit()
    
    # Try to delete without force flag
    response = await client.delete(f"/api/jobs/{job_id}")
    
    # Should be rejected with 409
    assert response.status_code == 409
    assert "Cannot delete job with" in response.json()["detail"]
    assert "force=true" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_job_with_tasks_cascade_with_force(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that force=true allows cascade delete of job and tasks."""
    from app.models.application_task import ApplicationTask
    from app.models.application_run import ApplicationRun
    from sqlalchemy import select
    
    # Create a run
    run = ApplicationRun(user_id=str(test_user.id), status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create a job
    job = JobPosting(
        job_url="https://example.com/job/cascade",
        apply_url="https://example.com/apply/cascade",
        job_title="To Force Delete"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    job_id = job.id

    # Create another job for the second task (UNIQUE constraint on run_id+job_id)
    job2 = JobPosting(
        job_url="https://example.com/job/cascade2",
        apply_url="https://example.com/apply/cascade2",
        job_title="Also To Delete"
    )
    db.add(job2)
    await db.commit()
    await db.refresh(job2)
    job2_id = job2.id

    # Create tasks for these jobs
    tasks = [
        ApplicationTask(
            run_id=str(run.id),
            job_id=job_id,
            state="QUEUED"
        ),
        ApplicationTask(
            run_id=str(run.id),
            job_id=job2_id,  # Different job to avoid UNIQUE constraint
            state="FAILED"
        )
    ]
    db.add_all(tasks)
    await db.commit()
    task_ids = [task.id for task in tasks]    # Delete first job with force flag
    response = await client.delete(f"/api/jobs/{job_id}?force=true")
    assert response.status_code == 204

    # Verify first job is deleted
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    assert result.scalar_one_or_none() is None

    # Verify its task is also deleted (cascade)
    result = await db.execute(select(ApplicationTask).where(ApplicationTask.id == task_ids[0]))
    assert result.scalar_one_or_none() is None
    
    # Second task should still exist (different job)
    result = await db.execute(select(ApplicationTask).where(ApplicationTask.id == task_ids[1]))
    assert result.scalar_one_or_none() is not None
# ============================================================
# EDGE CASE & INTEGRATION TESTS
# ============================================================

@pytest.mark.asyncio
async def test_pagination_boundary_conditions(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test pagination edge cases (skip > total, limit = 0, negative values)."""
    # Create 5 jobs
    jobs = [
        JobPosting(
            job_url=f"https://example.com/job/{i}",
            apply_url=f"https://example.com/apply/{i}"
        )
        for i in range(5)
    ]
    db.add_all(jobs)
    await db.commit()
    
    # Skip beyond available jobs
    response = await client.get("/api/jobs/?skip=100")
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # Limit at maximum (100)
    response = await client.get("/api/jobs/?limit=100")
    assert response.status_code == 200
    assert len(response.json()) == 5
    
    # Invalid limit (> 100) should be rejected by query validation
    response = await client.get("/api/jobs/?limit=101")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_job_returns_correct_structure(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test that GET /jobs/{id} returns all expected fields."""
    job = JobPosting(
        job_url="https://example.com/job/test",
        apply_url="https://example.com/apply/test",
        job_title="Test Job",
        company_name="Test Co",
        source="greenhouse",
        skills=["Python", "SQL"]
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    response = await client.get(f"/api/jobs/{job.id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all fields are present
    required_fields = [
        "id", "job_url", "apply_url", "source", "job_title",
        "company_name", "location_text", "work_mode", "employment_type",
        "industry", "description_raw", "description_clean", "skills",
        "has_been_applied_to"
    ]
    for field in required_fields:
        assert field in data


@pytest.mark.asyncio
async def test_create_multiple_jobs_same_company(
    client: AsyncClient,
    test_user: User
):
    """Test creating multiple different jobs at the same company."""
    jobs_data = [
        {
            "job_url": f"https://example.com/job/{i}",
            "apply_url": f"https://example.com/apply/{i}",
            "job_title": f"Position {i}",
            "company_name": "Same Company"
        }
        for i in range(3)
    ]
    
    created_ids = []
    for job_data in jobs_data:
        response = await client.post("/api/jobs/", json=job_data)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])
    
    # All should have different IDs
    assert len(set(created_ids)) == 3


@pytest.mark.asyncio
async def test_job_lifecycle_workflow(
    client: AsyncClient,
    test_user: User,
    db: AsyncSession
):
    """Test complete job lifecycle: create → list → get → delete."""
    # Create
    job_data = {
        "job_url": "https://example.com/job/lifecycle",
        "apply_url": "https://example.com/apply/lifecycle",
        "job_title": "Lifecycle Test"
    }
    create_response = await client.post("/api/jobs/", json=job_data)
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]
    
    # List (should include our job)
    list_response = await client.get("/api/jobs/")
    assert any(j["id"] == job_id for j in list_response.json())
    
    # Get specific job
    get_response = await client.get(f"/api/jobs/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["job_title"] == "Lifecycle Test"
    
    # Delete (no tasks, should work without force)
    delete_response = await client.delete(f"/api/jobs/{job_id}")
    assert delete_response.status_code == 204
    
    # Verify deleted
    get_after_delete = await client.get(f"/api/jobs/{job_id}")
    assert get_after_delete.status_code == 404
