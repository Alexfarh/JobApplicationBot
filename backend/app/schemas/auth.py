"""Authentication-related Pydantic schemas."""
from pydantic import BaseModel, EmailStr


class MagicLinkRequest(BaseModel):
    """Request to send magic link email."""
    email: EmailStr


class MagicLinkResponse(BaseModel):
    """Response after requesting magic link."""
    message: str
    email: str


class VerifyTokenRequest(BaseModel):
    """Request to verify magic link token."""
    token: str


class AuthResponse(BaseModel):
    """Response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str | None
    role: str
    profile_complete: bool
