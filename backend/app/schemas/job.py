"""Job-related Pydantic schemas."""
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class JobBase(BaseModel):
    """Base schema with common job posting fields."""
    job_url: str
    apply_url: str
    source: Optional[str] = None  # e.g., "greenhouse", "workday"
    external_job_id: Optional[str] = None  # e.g., Greenhouse job ID for deduplication
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    location_text: Optional[str] = None
    work_mode: Optional[str] = None  # remote | hybrid | onsite
    employment_type: Optional[str] = None  # full-time | contract
    industry: Optional[str] = None
    description_raw: Optional[str] = None
    description_clean: Optional[str] = None
    skills: Optional[list[str]] = None


class JobCreate(JobBase):
    """Schema for creating a new job posting."""
    pass


class JobResponse(JobBase):
    """Schema for job posting response."""
    id: int
    has_been_applied_to: bool
    
    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Schema for paginated job list response."""
    jobs: list[JobResponse]
    total: int
    skip: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)


class JobDiscoveryResponse(BaseModel):
    company_name: str
    job_title: str
    location_text: Optional[str]
    employment_type: Optional[str]  # internship / co-op / new grad / etc.
    work_mode: Optional[str]  # remote/hybrid/onsite
    description_raw: Optional[str]
    description_clean: Optional[str]
    apply_url: str
    ats_type: Optional[Literal["greenhouse", "lever", "other"]]
    inferred_role_category: Optional[str]  # backend/devops/ai/agentic
    inferred_seniority: Optional[str]  # internship/new grad/other

    # Salary fields
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_unit: Optional[Literal["hourly", "annual"]]
    salary_currency: Optional[str]
    salary_source: Optional[Literal["feed", "scraped", "inferred", "unknown"]]

    # Matching fields
    match_score: Optional[int]  # 0–100
    salary_meets_expectations: Optional[bool]  # or None for unknown
    mismatch_reasons: Optional[List[str]]

    # Extra fields for UI/debug
    source_company_url: Optional[str]
    posted_at: Optional[datetime]
    # Add more as needed
