"""
Jobs API endpoints.
Handles job posting CRUD operations.
"""
import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.services.job_discovery import discover_greenhouse_for_targets
from app.services.job_ingestion import seed_companies, ingest_all_greenhouse_companies
from app.database import get_db
from app.models.job_posting import JobPosting
from app.models.company import Company
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.job import JobCreate, JobDiscoveryResponse, JobResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Endpoints

@router.post("/ingest", response_model=Dict[str, int], status_code=200)
async def ingest_greenhouse_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger job ingestion from Greenhouse for all target companies.
    
    Flow:
    1. Seeds the companies table with all Greenhouse companies
    2. Fetches jobs from each company's Greenhouse board
    3. Creates/updates jobs in the database using the create_job logic
    
    Returns a summary dict with company names and job counts ingested.
    """
    try:
        import sys, ssl, os
        logger.info(f"Starting job ingestion triggered by user: {current_user.id}")
        logger.info(f"PY={sys.executable} OPENSSL={ssl.OPENSSL_VERSION}")
        logger.info(f"HTTPS_PROXY={os.getenv('HTTPS_PROXY')} HTTP_PROXY={os.getenv('HTTP_PROXY')} NO_PROXY={os.getenv('NO_PROXY')}")
        
        # Step 1: Seed companies table
        await seed_companies(db)
        logger.info("Companies table seeded")
        
        # Step 2: Define create_job logic as a callable
        async def create_job_wrapper(job: JobCreate, company_id: str, db: AsyncSession):
            # Check if job already exists by apply_url
            result = await db.execute(
                select(JobPosting).where(JobPosting.apply_url == job.apply_url)
            )
            existing_job = result.scalar_one_or_none()
            
            if existing_job:
                if existing_job.has_been_applied_to:
                    logger.info(f"Job already applied to, skipping: {job.apply_url}")
                    return None
                else:
                    logger.info(f"Job exists but not applied, updating: {job.apply_url}")
                    return existing_job
            
            # Create new job
            new_job = JobPosting(
                company_id=company_id,
                external_job_id=job.external_job_id or "unknown",  # Use provided ID or fallback
                ats_type="greenhouse",
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
            
            logger.info(f"Created new job: {job.job_title} at {job.company_name}")
            return new_job
        
        # Step 3: Ingest jobs from all companies
        logger.info(f"About to call ingest_all_greenhouse_companies from module: {ingest_all_greenhouse_companies.__module__}")
        print(f"DEBUG API: Calling ingest_all_greenhouse_companies: {ingest_all_greenhouse_companies}", flush=True)
        results = await ingest_all_greenhouse_companies(
            db,
            create_job_wrapper,
            current_user=current_user,
            min_match_score=50  # Only ingest jobs with 50+ match score
        )
        print(f"DEBUG API: Got results: {results}", flush=True)
        
        logger.info(f"Job ingestion completed. Results: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error during job ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Job ingestion failed: {str(e)}")


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


@router.get("/", response_model=list[JobResponse])
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


@router.get("/applicable", response_model=List[Dict], status_code=200)
async def get_applicable_jobs(
    min_score: Optional[int] = Query(50, description="Minimum match score (0-100)"),
    limit: Optional[int] = Query(50, description="Maximum number of results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get jobs applicable to the current user based on their profile and resume.
    
    Scoring factors:
    - Skill match: Resume skills vs job description
    - Work mode preference: Remote/hybrid/onsite
    - Seniority level: Junior/mid/senior matching
    - Location: Remote or location match
    
    Returns:
        List of applicable jobs sorted by match score (highest first)
    """
    from app.services.job_matching import get_applicable_jobs as score_jobs
    
    # Get active, unapplied jobs from database
    result = await db.execute(
        select(JobPosting).where(
            and_(
                JobPosting.is_active == True,
                JobPosting.has_been_applied_to == False
            )
        )
    )
    jobs = result.scalars().all()
    
    # Get resume text if available
    resume_text = None
    if current_user.resume_data:
        try:
            resume_text = current_user.resume_data.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Could not decode resume for user {current_user.id}: {e}")
    
    # Score and filter jobs
    applicable_jobs = score_jobs(
        jobs=jobs,
        user=current_user,
        resume_text=resume_text,
        min_score=min_score,
    )
    
    # Format response
    results = []
    for job, score, mismatches in applicable_jobs[:limit]:
        results.append({
            "id": job.id,
            "company_name": job.company_name,
            "job_title": job.job_title,
            "location": job.location_text,
            "work_mode": job.work_mode,
            "apply_url": job.apply_url,
            "match_score": score,
            "mismatch_reasons": mismatches,
            "employment_type": job.employment_type,
            "description_preview": (job.description_raw or "")[:200] + "...",
        })
    
    logger.info(f"Found {len(results)} applicable jobs for user {current_user.id}")
    return results

