from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base
from app.database_types import GUID, JSON


class RunStatus(str, enum.Enum):
    """Application run status."""
    QUEUED = "queued"      # Run created, waiting to be started
    RUNNING = "running"    # Currently being processed
    COMPLETED = "completed" # All tasks finished


class ApplicationRun(Base):
    __tablename__ = "application_runs"
    
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    
    # Optional name and description for UX (e.g., "Monday batch", "Tech jobs in SF")
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    
    # Status: queued | running | completed
    # Only ONE run can have status='running' at a time (enforced by API)
    status = Column(String, nullable=False, default="queued")
    
    # Configuration snapshot
    settings_snapshot = Column(JSON, nullable=True)
    batch_size = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # When processing actually began
    completed_at = Column(DateTime, nullable=True)  # When all tasks finished
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tasks = relationship("ApplicationTask", back_populates="run", cascade="all, delete-orphan")
