"""
Jobs API endpoints.
Handles job posting CRUD operations.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, HttpUrl, ConfigDict

from app.database import get_db
from app.models.job_posting import JobPosting
from app.models.user import User
from app.api.auth import get_current_user

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()



# ============================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================

class JobBase(BaseModel):
    """Base schema with common job posting fields."""
    job_url: str
    apply_url: str
    source: Optional[str] = None  # e.g., "greenhouse", "workday"
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    location_text: Optional[str] = None
    work_mode: Optional[str] = None  # remote | hybrid | onsite
    employment_type: Optional[str] = None  # full-time | contract
    industry: Optional[str] = None
    description_raw: Optional[str] = None
    description_clean: Optional[str] = None
    skills: Optional[List[str]] = None


class JobCreate(JobBase):
    """Schema for creating a new job posting."""
    pass


class JobResponse(JobBase):
    """Schema for job posting response."""
    id: int
    has_been_applied_to: bool
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(
    job: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new job posting.
    
    Behavior:
    - If job exists and has_been_applied_to=False: Returns existing job (can be queued for retry)
    - If job exists and has_been_applied_to=True: Returns 409 (already SUBMITTED, skip in ingestion)
    - If job doesn't exist: Creates new job
    
    Caller (job ingestion) should handle 409 by skipping that job and continuing.
    
    Note: Only SUBMITTED tasks set has_been_applied_to=True.
    FAILED and EXPIRED tasks leave it False, allowing retry.
    """
    # Check if job already exists by apply_url
    result = await db.execute(
        select(JobPosting).where(JobPosting.apply_url == job.apply_url)
    )
    existing_job = result.scalar_one_or_none()
    
    if existing_job:
        if existing_job.has_been_applied_to:
            # Job was successfully submitted - caller should skip this job
            logger.info(f"Job already applied to, returning 409: {job.apply_url}")
            raise HTTPException(
                status_code=409,
                detail=f"Already applied to this job on {existing_job.last_applied_at}"
            )
        else:
            # Job exists but not yet applied (could be FAILED/EXPIRED) - allow retry
            logger.info(f"Job exists but not applied, returning for retry: {job.apply_url}")
            return existing_job
    
    # Create new job
    new_job = JobPosting(
        job_url=job.job_url,
        apply_url=job.apply_url,
        source=job.source,
        job_title=job.job_title,
        company_name=job.company_name,
        location_text=job.location_text,
        work_mode=job.work_mode,
        employment_type=job.employment_type,
        industry=job.industry,
        description_raw=job.description_raw,
        description_clean=job.description_clean,
        skills=job.skills,
        has_been_applied_to=False
    )
    
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    
    logger.info(f"Created job {new_job.id}: {job.job_title} at {job.company_name}")
    
    return new_job


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    applied: Optional[bool] = Query(None, description="Filter by has_been_applied_to"),
    company: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    source: Optional[str] = Query(None, description="Filter by source platform"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List job postings with optional filtering.
    Returns paginated results.
    """
    # Build query with filters
    query = select(JobPosting)
    
    filters = []
    if applied is not None:
        filters.append(JobPosting.has_been_applied_to == applied)
    if company:
        filters.append(JobPosting.company_name.ilike(f"%{company}%"))
    if source:
        filters.append(JobPosting.source == source)
    if work_mode:
        filters.append(JobPosting.work_mode == work_mode)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    logger.info(f"Listed {len(jobs)} jobs (filters: applied={applied}, company={company})")
    
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific job posting by ID.
    """
    result = await db.execute(
        select(JobPosting).where(JobPosting.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: int,
    force: bool = Query(False, description="Force delete even if tasks exist"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a job posting.
    
    By default, prevents deletion if any tasks exist (safe mode).
    Use ?force=true to cascade delete tasks (DANGEROUS - removes application history).
    
    Recommended: Don't use this endpoint. Jobs should persist for historical tracking.
    Instead, filter by has_been_applied_to to hide already-applied jobs from UI.
    """
    from app.models.application_task import ApplicationTask
    
    result = await db.execute(
        select(JobPosting).where(JobPosting.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check for associated tasks
    task_result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.job_id == job_id)
    )
    tasks = task_result.scalars().all()
    
    if tasks and not force:
        # Prevent accidental deletion of jobs with task history
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete job with {len(tasks)} associated tasks. Use ?force=true to override (not recommended)."
        )
    
    # Delete tasks if force=true
    if tasks:
        for task in tasks:
            await db.delete(task)
        logger.warning(f"Force deleting job {job_id} and {len(tasks)} tasks")
    
    # Delete the job
    await db.delete(job)
    await db.commit()
    
    logger.info(f"Deleted job {job_id}")
    
    return None
