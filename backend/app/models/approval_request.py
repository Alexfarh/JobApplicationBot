from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("application_tasks.id"), nullable=False, unique=True)
    
    # Status: pending | approved | expired | cancelled
    status = Column(String, nullable=False, default="pending")
    
    # Channel: email (only option in V1)
    channel = Column(String, nullable=False, default="email")
    
    # One-time approval token
    approval_token = Column(String, nullable=False, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # default: created_at + 20 minutes
    approved_at = Column(DateTime, nullable=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(minutes=20)
        if not self.approval_token:
            self.approval_token = str(uuid.uuid4())
