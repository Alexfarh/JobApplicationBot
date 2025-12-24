from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
import uuid

from app.database import Base
from app.database_types import GUID


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    task_id = Column(GUID, ForeignKey("application_tasks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Form data captured at final review step
    form_data = Column(JSON, nullable=False, default=list)
    
    # Preview URL (optional)
    preview_url = Column(String, nullable=True)
    
    # Status: pending | approved | rejected | expired
    status = Column(String, nullable=False, default="pending")
    
    # Channel: email (only option in V1)
    channel = Column(String, nullable=False, default="email")
    
    # One-time approval token (generated automatically)
    approval_token = Column(String, nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    approved_at = Column(DateTime, nullable=True)
