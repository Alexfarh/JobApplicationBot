"""
Job ingestion service.
Fetches jobs from ATS boards (Greenhouse, Lever, etc.) and stores them in the database.
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiohttp

from app.models.company import Company
from app.models.user import User
from app.schemas.job import JobCreate
from app.services.job_discovery import fetch_greenhouse_jobs, normalize_greenhouse_job
from app.services.job_matching import (
    ResumeParser,
    check_job_type_match,
    check_seniority_match,
    calculate_job_match_score
)

logger = logging.getLogger(__name__)

# Greenhouse companies to ingest (verified to have live job postings)
GREENHOUSE_COMPANIES = [
    {"company_name": "Stripe", "board_token": "stripe"},           # 500+ jobs
    {"company_name": "Databricks", "board_token": "databricks"},   # 680 jobs
    {"company_name": "Figma", "board_token": "figma"},             # 155 jobs
    {"company_name": "Anthropic", "board_token": "anthropic"},     # 301 jobs
    {"company_name": "Cloudflare", "board_token": "cloudflare"},   # Live board
    {"company_name": "Airbnb", "board_token": "airbnb"},           # Live board
    {"company_name": "Coinbase", "board_token": "coinbase"},       # Live board
    {"company_name": "Elastic", "board_token": "elastic"},         # Live board
    {"company_name": "MongoDB", "board_token": "mongodb"},         # Live board
    {"company_name": "Vercel", "board_token": "vercel"},           # Live board
    {"company_name": "Asana", "board_token": "asana"},             # Live board
    {"company_name": "Scale AI", "board_token": "scaleai"},        # Live board
    {"company_name": "Roblox", "board_token": "roblox"},           # Live board
]


async def seed_companies(db: AsyncSession) -> None:
    """
    Seed the companies table with Greenhouse companies.
    Creates or updates company records.
    """
    for company_data in GREENHOUSE_COMPANIES:
        # Check if company already exists
        result = await db.execute(
            select(Company).where(Company.company_name == company_data["company_name"])
        )
        existing_company = result.scalar_one_or_none()
        
        if not existing_company:
            # Create new company
            company = Company(
                id=str(__import__('uuid').uuid4()),
                company_name=company_data["company_name"],
                ats_type="greenhouse",
                board_token=company_data["board_token"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(company)
            logger.info(f"Seeded company: {company_data['company_name']}")
        else:
            logger.info(f"Company already exists: {company_data['company_name']}")
    
    await db.commit()


async def ingest_greenhouse_jobs(
    company_id: str, 
    board_token: str, 
    company_name: str, 
    db: AsyncSession, 
    session: aiohttp.ClientSession,
    current_user: Optional[User] = None,
    min_match_score: int = 50
) -> int:
    """
    Fetch jobs from a Greenhouse board and create them using the create_job logic.
    Uses the discovery service functions for fetching and normalization.
    Optionally filters jobs based on user profile and resume.
    Returns the number of jobs ingested/updated.
    """
    # Fetch raw jobs from Greenhouse API
    print(f"DEBUG ingest_greenhouse_jobs: board_token={board_token}, session={session}", flush=True)
    logger.info(f"fetch_greenhouse_jobs from: {fetch_greenhouse_jobs.__module__}")
    logger.info(f"About to fetch from {board_token}")
    print(f"DEBUG: Calling fetch_greenhouse_jobs with board_token={board_token}", flush=True)
    raw_jobs = await fetch_greenhouse_jobs(board_token, session)
    print(f"DEBUG: fetch_greenhouse_jobs returned {len(raw_jobs)} jobs", flush=True)
    logger.info(f"Fetched {len(raw_jobs)} jobs from Greenhouse board: {board_token}")
    
    # Prepare user matching data if available
    user_skills = []
    user_seniority = None
    user_experience_years = None
    resume_text = None
    
    if current_user:
        # Try to extract from resume if available
        if current_user.resume_data:
            try:
                resume_text = current_user.resume_data.decode('utf-8', errors='ignore')
                user_skills = ResumeParser.extract_skills(resume_text)
                user_seniority = ResumeParser.infer_seniority(resume_text)
                user_experience_years = ResumeParser.extract_experience_years(resume_text)
                logger.info(
                    f"Parsed resume: {len(user_skills)} skills, seniority={user_seniority}, "
                    f"years={user_experience_years}"
                )
            except Exception as e:
                logger.warning(f"Could not parse resume for filtering: {e}")
        
        # If no resume, assume junior level for internship filtering
        if not user_seniority and current_user.internship_only:
            user_seniority = "junior"
            logger.info("No resume found, assuming junior level for internship filtering")
    
    ingested_count = 0
    skipped_count = 0
    
    for raw_job in raw_jobs:
        # Normalize the job using discovery service
        normalized_job = normalize_greenhouse_job(raw_job, company_name)
        
        if not normalized_job:
            logger.warning(f"Skipped malformed job from {company_name}")
            skipped_count += 1
            continue
        
        # Filter based on user profile if provided
        if current_user:
            job_title = normalized_job.job_title or ""
            job_desc = normalized_job.description_raw or ""
            
            # Get user preferences
            preferred_job_types = current_user.preferred_job_types or []
            
            # HARD FILTER 1: Job type must match preferred types
            is_valid_type, type_reason = check_job_type_match(
                job_title, job_desc, preferred_job_types
            )
            if not is_valid_type:
                logger.debug(
                    f"Skipped non-matching job type: {job_title} ({type_reason})"
                )
                skipped_count += 1
                continue
            
            # HARD FILTER 2: Seniority must match
            is_valid_seniority, seniority_reason = check_seniority_match(
                user_seniority, job_title, job_desc
            )
            if not is_valid_seniority:
                logger.debug(
                    f"Skipped seniority mismatch: {job_title} ({seniority_reason})"
                )
                skipped_count += 1
                continue
            
            # If job passes hard filters and we have resume data, calculate score
            if resume_text and user_skills:
                from app.models.job_posting import JobPosting
                temp_job = JobPosting(
                    id=0,
                    company_id=company_id,
                    external_job_id="temp",
                    ats_type="greenhouse",
                    source="greenhouse",
                    job_url=raw_job.get("absolute_url", ""),
                    apply_url=normalized_job.apply_url,
                    company_name=company_name,
                    job_title=normalized_job.job_title,
                    location_text=normalized_job.location_text,
                    work_mode=normalized_job.work_mode,
                    employment_type=normalized_job.employment_type,
                    industry=None,
                    description_raw=normalized_job.description_raw,
                    description_clean=normalized_job.description_clean,
                    skills=user_skills,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                    is_active=True,
                    has_been_applied_to=False,
                )
                
                score, mismatches = calculate_job_match_score(
                    temp_job,
                    user_skills=user_skills,
                    user_location=current_user.address_city,
                )
                
                if score < min_match_score:
                    logger.debug(
                        f"Skipped low-match job: {normalized_job.job_title} "
                        f"(score={score}, mismatches={mismatches})"
                    )
                    skipped_count += 1
                    continue
        
        # Create JobCreate request from normalized data
        job_create = JobCreate(
            job_url=raw_job.get("absolute_url", ""),
            apply_url=normalized_job.apply_url,
            source="greenhouse",
            external_job_id=str(raw_job.get("id", "unknown")),  # Convert ID to string for Pydantic
            job_title=normalized_job.job_title,
            company_name=company_name,
            location_text=normalized_job.location_text,
            work_mode=normalized_job.work_mode,
            employment_type=normalized_job.employment_type,
            industry=None,
            description_raw=normalized_job.description_raw,
            description_clean=normalized_job.description_clean,
            skills=user_skills if user_skills else None
        )
        
        # Create job directly in database
        try:
            from app.models.job_posting import JobPosting
            job_posting = JobPosting(
                company_id=company_id,
                external_job_id=job_create.external_job_id,
                ats_type="greenhouse",
                source="greenhouse",
                job_url=job_create.job_url,
                apply_url=job_create.apply_url,
                company_name=job_create.company_name,
                job_title=job_create.job_title,
                location_text=job_create.location_text,
                work_mode=job_create.work_mode,
                employment_type=job_create.employment_type,
                industry=job_create.industry,
                description_raw=job_create.description_raw,
                description_clean=job_create.description_clean,
                skills=job_create.skills,
                raw_json=raw_job,
                first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(),
                is_active=True,
                has_been_applied_to=False,
            )
            db.add(job_posting)
            await db.flush()
            ingested_count += 1
            logger.debug(f"Ingested job: {job_create.job_title}")
        except Exception as e:
            error_msg = str(e)
            # Handle unique constraint violations gracefully (duplicate job)
            if "uq_company_external_id_ats" in error_msg or "UNIQUE constraint failed" in error_msg:
                logger.debug(f"Job already exists (duplicate): {job_create.job_title} from {company_name}")
                skipped_count += 1
            else:
                logger.error(f"Error ingesting job {job_create.job_title}: {error_msg}")
                skipped_count += 1
    
    # Update last_ingested_at
    company = await db.execute(select(Company).where(Company.id == company_id))
    company_obj = company.scalar_one_or_none()
    if company_obj:
        company_obj.last_ingested_at = datetime.utcnow()
        await db.commit()
    
    logger.info(
        f"Ingested {ingested_count} jobs for company: {company_name} "
        f"(skipped {skipped_count} non-applicable jobs)"
    )
    return ingested_count


async def ingest_all_greenhouse_companies(
    db: AsyncSession, 
    current_user: Optional[User] = None,
    min_match_score: int = 50
) -> Dict[str, int]:
    """
    Ingest jobs for all Greenhouse companies.
    Optionally filters jobs based on current user's profile and resume.
    Returns a summary of ingestion results.
    """
    import ssl
    results = {}
    
    # Always disable SSL verification in dev (no cert verification needed for public APIs)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    logger.info(f"Created connector with SSL disabled: {connector}")
    
    async with aiohttp.ClientSession(connector=connector, trust_env=False) as session:
        logger.info(f"Session created: {session} with connector: {session.connector} trust_env=False")
        for company_data in GREENHOUSE_COMPANIES:
            company_name = company_data["company_name"]
            board_token = company_data["board_token"]
            
            # Get company ID from database
            result = await db.execute(
                select(Company).where(Company.company_name == company_name)
            )
            company = result.scalar_one_or_none()
            
            if not company:
                logger.warning(f"Company not found in database: {company_name}")
                results[company_name] = 0
                continue
            
            try:
                count = await ingest_greenhouse_jobs(
                    company.id,
                    board_token,
                    company_name,
                    db,
                    session,
                    current_user=current_user,
                    min_match_score=min_match_score
                )
                results[company_name] = count
                logger.info(f"Successfully ingested {count} jobs for {company_name}")
            except Exception as e:
                logger.error(f"Error ingesting jobs for {company_name}: {str(e)}")
                results[company_name] = 0
    
    return results
