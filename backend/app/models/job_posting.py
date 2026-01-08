from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from app.database import Base
from app.database_types import JSON, GUID


class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company ID from Greenhouse
    company_id = Column(GUID, nullable=False, index=True)
    
    # External job ID from ATS (e.g., Greenhouse job ID)
    external_job_id = Column(String, nullable=False, index=True)
    
    # ATS type used to fetch this job
    ats_type = Column(String, nullable=False, default="greenhouse")  # e.g., "greenhouse", "lever"
    
    # Source & URLs
    source = Column(String, nullable=True)  # e.g., "greenhouse", "workday"
    job_url = Column(String, nullable=True)
    apply_url = Column(String, nullable=False, unique=True, index=True)
    
    # Job details
    company_name = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    location_text = Column(String, nullable=True)
    work_mode = Column(String, nullable=True)  # remote | hybrid | onsite
    employment_type = Column(String, nullable=True)  # full-time | contract | etc
    industry = Column(String, nullable=True)
    
    # Description
    description_raw = Column(Text, nullable=True)
    description_clean = Column(Text, nullable=True)
    
    # Skills (list of strings)
    skills = Column(JSON, nullable=True)  # e.g., ["Python", "React", "AWS"]
    
    # Ingestion tracking
    raw_json = Column(JSON, nullable=True)  # Full raw response from ATS for debugging/future extraction
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When first ingested
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # Last update from ATS
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # False if job was removed from ATS
    
    # Application tracking (denormalized for fast duplicate detection)
    has_been_applied_to = Column(Boolean, default=False, nullable=False)
    last_applied_at = Column(DateTime, nullable=True)
    
    # Unique constraint: one job per company per ATS
    __table_args__ = (
        UniqueConstraint("company_id", "external_job_id", "ats_type", name="uq_company_external_id_ats"),
    )
