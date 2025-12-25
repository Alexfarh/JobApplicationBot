"""Task-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class TaskResponse(BaseModel):
    """Schema for task response."""
    id: UUID
    run_id: UUID
    job_id: int
    state: str
    priority: int
    attempt_count: int
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    queued_at: datetime
    started_at: Optional[datetime] = None
    last_state_change_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ResumeResponse(BaseModel):
    """Response after resuming a task."""
    task_id: str
    old_state: str
    new_state: str
    priority: int
    message: str
