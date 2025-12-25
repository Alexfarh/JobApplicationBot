"""Run-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CreateRunRequest(BaseModel):
    """Request to create a new application run."""
    name: str
    description: Optional[str] = None


class RunResponse(BaseModel):
    """Response with run details."""
    id: str
    user_id: str
    name: Optional[str]
    description: Optional[str]
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime
    
    # Task counts
    total_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    submitted_tasks: int = 0
    failed_tasks: int = 0
    rejected_tasks: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class RunListResponse(BaseModel):
    """List of runs."""
    runs: list[RunResponse]
    total: int
