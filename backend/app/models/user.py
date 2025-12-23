from datetime import datetime
from sqlalchemy import Column, String, DateTime
import uuid

from app.database import Base
from app.database_types import GUID


class User(Base):
    __tablename__ = "users"
    
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    
    # Magic link authentication
    magic_link_token = Column(String, nullable=True)
    magic_link_expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
