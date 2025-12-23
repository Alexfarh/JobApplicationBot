"""
Authentication endpoints for magic link login.

Phase 1: Dev mode - prints magic link to console
Future: Send email with magic link
"""
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.config import settings


router = APIRouter()


# Request/Response Models (Pydantic schemas)
class MagicLinkRequest(BaseModel):
    """Request body for requesting a magic link."""
    email: EmailStr  # Automatically validates email format


class MagicLinkResponse(BaseModel):
    """Response after requesting magic link."""
    message: str
    email: str


class VerifyTokenRequest(BaseModel):
    """Request body for verifying a magic link token."""
    token: str


class AuthResponse(BaseModel):
    """Response after successful authentication."""
    user_id: str
    email: str
    token: str  # In real app, this would be a JWT


# Endpoints
@router.post("/request-magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    request: MagicLinkRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a magic link for passwordless login.
    
    In dev mode: Prints link to console
    In prod mode: Sends email
    
    Returns:
        200: Magic link generated successfully
        500: Database or system error
    """
    try:
        # Get or create user
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(email=request.email)
            db.add(user)
        
        # Generate magic link token
        user.magic_link_token = uuid4().hex
        user.token_expires_at = datetime.utcnow() + timedelta(
            minutes=settings.magic_link_ttl_minutes
        )
        
        await db.commit()
        
        # Build magic link URL (uses frontend URL from config)
        magic_link = f"{settings.get_frontend_url()}/auth/verify?token={user.magic_link_token}"
        
        # Dev mode: print to console
        if settings.email_mode == "dev":
            print("\n" + "="*60)
            print("🔐 MAGIC LINK LOGIN")
            print("="*60)
            print(f"Email: {user.email}")
            print(f"Link:  {magic_link}")
            print(f"Expires: {user.token_expires_at}")
            print("="*60 + "\n")
        else:
            # Production: send email
            # TODO: Implement email sending in future phase
            pass
        
        return MagicLinkResponse(
            message="Magic link sent! Check your email (or console in dev mode).",
            email=user.email
        )
    
    except Exception as e:
        # Rollback any pending database changes
        await db.rollback()
        # Log the error (in production, use proper logging)
        print(f"❌ Error generating magic link: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate magic link. Please try again."
        )


@router.post("/verify-token", response_model=AuthResponse)
async def verify_token(
    request: VerifyTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify magic link token and authenticate user.
    
    Returns user info and session token.
    
    Returns:
        200: Token valid, user authenticated
        401: Invalid or expired token
        500: Database or system error
    """
    try:
        # Find user with this token
        result = await db.execute(
            select(User).where(User.magic_link_token == request.token)
        )
        user = result.scalar_one_or_none()
        
        # Validate token exists
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid token. Please request a new magic link."
            )
        
        # Validate token not expired
        if user.token_expires_at < datetime.utcnow():
            # Clear expired token
            user.magic_link_token = None
            user.token_expires_at = None
            await db.commit()
            
            raise HTTPException(
                status_code=401,
                detail="Token expired. Please request a new magic link."
            )
        
        # Token is valid - clear it (one-time use)
        user.magic_link_token = None
        user.token_expires_at = None
        await db.commit()
        
        # In a real app, generate JWT here
        # For now, return user ID as "token"
        return AuthResponse(
            user_id=str(user.id),
            email=user.email,
            token=str(user.id)  # Phase 1: simple user_id as token
        )
    
    except HTTPException as http_err:
        # Re-raise HTTP exceptions (401 errors with messages already set above)
        # These are expected user errors, not system failures
        raise http_err
    
    except Exception as e:
        # Catch any unexpected errors (database, network, etc.)
        await db.rollback()
        print(f"❌ Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed. Please try again."
        )
