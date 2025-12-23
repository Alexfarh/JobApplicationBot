from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime
from app.database import Base


class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Source & URLs
    source = Column(String, nullable=True)  # e.g., "greenhouse", "workday"
    job_url = Column(String, nullable=False)
    apply_url = Column(String, nullable=False)
    
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
    
    # Application tracking (denormalized for fast duplicate detection)
    has_been_applied_to = Column(Boolean, default=False, nullable=False)
    last_applied_at = Column(DateTime, nullable=True)
