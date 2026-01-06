"""Profile-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl


class ProfileUpdateRequest(BaseModel):
    """Request body for updating user profile."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    address_country: Optional[str] = None
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None

    # Target companies for job discovery (user-provided or default)
    target_companies: Optional[list[str]] = None

    # Salary expectation fields (optional, used for job matching)
    expected_salary_hourly_min: Optional[int] = 30
    expected_salary_annual_min: Optional[int] = 65000
    expected_salary_currency: Optional[str] = "CAD"
    salary_flexibility_note: Optional[str] = None


class MandatoryQuestionsRequest(BaseModel):
    """Request body for updating mandatory questions."""
    work_authorization: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    gender: Optional[str] = None
    ethnicity: Optional[str] = None
    referral_source: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None


class PreferencesRequest(BaseModel):
    """Request body for updating automation preferences."""
    optimistic_mode: Optional[bool] = None
    require_approval: Optional[bool] = None
    preferred_platforms: Optional[list[str]] = None


class ProfileResponse(BaseModel):
    """Response with complete user profile."""
    # User ID and email
    user_id: str
    email: str
    role: str
    
    # Personal information
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    address_country: Optional[str] = None
    
    # Professional URLs
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    # Target companies for job discovery (user-provided or default)
    target_companies: Optional[list[str]] = None

    # Salary expectation fields (optional, used for job matching)
    expected_salary_hourly_min: Optional[int] = 30
    expected_salary_annual_min: Optional[int] = 65000
    expected_salary_currency: Optional[str] = "CAD"
    salary_flexibility_note: Optional[str] = None
    
    # Resume info
    resume_uploaded: bool = False
    resume_filename: Optional[str] = None
    resume_uploaded_at: Optional[datetime] = None
    resume_size_bytes: Optional[int] = None
    
    # Data fields
    mandatory_questions: Optional[dict] = None
    preferences: Optional[dict] = None
    profile_complete: bool = False
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
