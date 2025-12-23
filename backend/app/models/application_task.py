from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.database_types import GUID


class TaskState(str, Enum):
    """Valid states for application tasks"""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    NEEDS_AUTH = "NEEDS_AUTH"
    NEEDS_USER = "NEEDS_USER"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class ApplicationTask(Base):
    __tablename__ = "application_tasks"
    
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    run_id = Column(GUID, ForeignKey("application_runs.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    
    # State machine
    state = Column(String, nullable=False, default=TaskState.QUEUED.value)
    
    # Queue priority (50 = default, 100 = resumed/boosted)
    priority = Column(Integer, nullable=False, default=50)
    
    # Retry tracking
    attempt_count = Column(Integer, nullable=False, default=0)
    
    # Error tracking
    last_error_code = Column(String, nullable=True)
    last_error_message = Column(Text, nullable=True)
    
    # Timestamps
    queued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    last_state_change_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    run = relationship("ApplicationRun", back_populates="tasks")
    
    __table_args__ = (
        # Prevent duplicate applications to same job in a run
        UniqueConstraint('run_id', 'job_id', name='uq_run_job'),
        
        # Index for efficient queue dequeue
        Index('idx_tasks_queue', 'run_id', 'state', 'priority', 'queued_at'),
    )
