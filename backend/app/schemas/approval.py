"""Approval-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FormField(BaseModel):
    """Schema for a single form field."""
    label: str
    value: str
    field_type: str = "text"  # text, select, checkbox, etc.


class ApprovalRequestCreate(BaseModel):
    """Schema for creating an approval request."""
    task_id: UUID
    form_data: list[FormField]
    preview_url: Optional[str] = None
    ttl_minutes: int = 20


class ApprovalResponse(BaseModel):
    """Schema for approval request response."""
    id: UUID
    task_id: UUID
    user_id: UUID
    form_data: list[FormField]
    preview_url: Optional[str] = None
    status: str
    expires_at: datetime
    created_at: datetime
    approved_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ApprovalAction(BaseModel):
    """Schema for approval/rejection action."""
    approved: bool
    notes: Optional[str] = None
