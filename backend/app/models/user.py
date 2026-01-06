from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, Text, JSON, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
import uuid
import enum

from app.database import Base
from app.database_types import GUID


class UserRole(str, enum.Enum):
    """User role for role-based access control (RBAC)."""
    USER = "user"  # Regular user - can only access own data
    ADMIN = "admin"  # Admin - can view all users, manage system settings


class User(Base):
    __tablename__ = "users"
    
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    
    # Role-based access control
    role = Column(
        SQLEnum(UserRole, name="user_role", create_type=True),
        nullable=False,
        default=UserRole.USER,
        index=True
    )
    
    # Magic link authentication
    magic_link_token = Column(String, nullable=True, index=True)  # Index for fast lookup
    magic_link_expires_at = Column(DateTime, nullable=True)
    
    # Security & audit fields
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime, nullable=True)  # Temporary account lock after too many failed attempts
    
    # Profile information (for auto-filling job applications)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Address fields
    address_street = Column(String(255), nullable=True)
    address_city = Column(String(100), nullable=True)
    address_state = Column(String(50), nullable=True)
    address_zip = Column(String(20), nullable=True)
    address_country = Column(String(100), nullable=True, default="United States")
    
    # Professional profiles
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    
    # Resume storage
    resume_data = Column(LargeBinary, nullable=True)  # Stores the actual file content
    resume_uploaded_at = Column(DateTime, nullable=True)
    resume_filename = Column(String(255), nullable=True)  # Original filename
    resume_size_bytes = Column(Integer, nullable=True)  # File size for validation
    
    # Mandatory questions (default answers for common application questions)
    # Structure: {"work_authorization": "US Citizen", "veteran": "no", "disability": "prefer_not_to_say", ...}
    mandatory_questions = Column(JSON, nullable=True, default=dict)
    
    # User preferences for automation behavior
    # Structure: {"optimistic_mode": true, "require_approval": true, "preferred_platforms": ["greenhouse"]}
    preferences = Column(
        JSON,
        nullable=True,
        default=lambda: {
            "optimistic_mode": True,
            "require_approval": True,
            "preferred_platforms": ["greenhouse"]
        }
    )

    # Target companies for job discovery (user-provided or default)
    # List of company names or URLs
    target_companies = Column(JSON, nullable=True, default=lambda: [
        "Google", "Meta", "Amazon", "Apple", "Netflix", "Microsoft", "NVIDIA", "OpenAI", "Anthropic", "Tesla",
        "Stripe", "Databricks", "Snowflake", "Cloudflare", "Shopify", "Uber", "Airbnb", "Coinbase", "Palantir", "Roblox",
        "Scale AI", "Hugging Face", "Mistral AI", "Figma", "Notion", "Asana", "Elastic", "MongoDB", "Confluent", "GitHub",
        "Vercel", "Supabase", "Render", "Replicate", "Weights & Biases", "Pinecone", "Cohere", "Perplexity AI", "Cursor", "Replit",
        "Jane Street", "Citadel", "Goldman Sachs", "Morgan Stanley", "Bloomberg", "RBC", "TD Bank", "SAP", "IBM", "Qualcomm"
    ])

    # Salary expectation fields (optional, used for job matching)
    expected_salary_hourly_min = Column(Integer, nullable=True, default=30)
    expected_salary_annual_min = Column(Integer, nullable=True, default=65000)
    expected_salary_currency = Column(String(10), nullable=True, default="CAD")
    salary_flexibility_note = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked due to failed login attempts."""
        if not self.account_locked_until:
            return False
        return datetime.utcnow() < self.account_locked_until
    
    def has_complete_profile(self) -> bool:
        """
        Check if user has completed minimum profile requirements for job applications.
        
        Required fields:
        - Full name
        - Email address
        - Phone number
        - Resume uploaded
        - Mandatory questions answered (all defined questions must have answers)
        """
        # Required fields must exist
        if not all([self.full_name, self.email, self.phone, self.resume_data]):
            return False
        
        # Mandatory questions must exist and have all required fields answered
        if not self.mandatory_questions:
            return False
        
        # All mandatory question fields that are defined must be answered
        required_questions = [
            'work_authorization',
            'veteran_status', 
            'disability_status',
            'gender',
            'ethnicity',
            'referral_source'
        ]
        
        # At least the critical questions must be answered
        critical_questions = ['work_authorization', 'veteran_status', 'disability_status']
        for question in critical_questions:
            if question not in self.mandatory_questions or not self.mandatory_questions[question]:
                return False
        
        return True
