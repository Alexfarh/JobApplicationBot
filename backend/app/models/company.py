"""Company model for job discovery ATS boards."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum
import uuid
import enum

from app.database import Base
from app.database_types import GUID


class ATSType(str, enum.Enum):
    """ATS type for job board discovery."""
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    OTHER = "other"


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    company_name = Column(String, nullable=False, unique=True, index=True)
    
    # ATS information
    ats_type = Column(
        SQLEnum(ATSType, name="ats_type", create_type=True),
        nullable=False,
        default=ATSType.GREENHOUSE,
        index=True
    )
    
    # Board token for accessing ATS API (e.g., Greenhouse board token)
    board_token = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_ingested_at = Column(DateTime, nullable=True)  # When we last fetched jobs from this company
