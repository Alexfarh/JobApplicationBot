"""Job-related Pydantic schemas."""
from typing import Optional
from pydantic import BaseModel, ConfigDict


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
    skills: Optional[list[str]] = None


class JobCreate(JobBase):
    """Schema for creating a new job posting."""
    pass


class JobResponse(JobBase):
    """Schema for job posting response."""
    id: int
    has_been_applied_to: bool
    
    model_config = ConfigDict(from_attributes=True)
