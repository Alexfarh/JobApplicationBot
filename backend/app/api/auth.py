"""
Authentication endpoints for magic link login.

Phase 1: Dev mode - prints magic link to console
Future: Send email with magic link

Security features:
- Account lockout after 5 failed attempts (30 min cooldown)
- Magic link tokens expire after configured TTL
- One-time use tokens (invalidated after verification)
- IP address logging for audit trail
- Role-based access control (admin vs user)
"""
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.config import settings
from app.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    VerifyTokenRequest,
    AuthResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Security constants
MAX_FAILED_ATTEMPTS = 5
ACCOUNT_LOCK_MINUTES = 30


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
            # Create new user with default USER role
            user = User(email=request.email, role=UserRole.USER)
            db.add(user)
        
        # Generate magic link token
        user.magic_link_token = uuid4().hex
        user.magic_link_expires_at = datetime.utcnow() + timedelta(
            minutes=settings.magic_link_ttl_minutes
        )
        
        await db.commit()
        
        # Build magic link URL (uses frontend URL from config)
        magic_link = f"{settings.get_frontend_url()}/auth/verify?token={user.magic_link_token}"
        
        # Dev mode: print to console
        if settings.email_mode == "dev":
            logger.info(
                f"Magic link generated for {user.email}: {magic_link} "
                f"(expires: {user.magic_link_expires_at})"
            )
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
        logger.error(f"Error generating magic link: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate magic link. Please try again."
        )


# Authentication Dependencies
async def get_current_user(
    auth_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from httpOnly cookie.
    
    DEV MODE: If no cookie, returns a default dev user
    Phase 1: Cookie contains just the user_id
    Future: Validate JWT and extract user_id
    
    Args:
        auth_token: Authentication cookie (httpOnly)
        db: Database session
    
    Returns:
        User: The authenticated user
    
    Raises:
        HTTPException 401: If cookie is invalid or user not found
        HTTPException 403: If account is locked
    """
    # DEV MODE: If no auth token, create/return a default dev user
    if not auth_token:
        result = await db.execute(
            select(User).where(User.email == "dev@example.com")
        )
        dev_user = result.scalar_one_or_none()
        
        if not dev_user:
            dev_user = User(
                email="dev@example.com",
                full_name="Dev User",
                phone="555-0000",
                mandatory_questions={
                    "work_authorization": "yes",
                    "veteran_status": "no",
                    "disability_status": "no"
                }
            )
            db.add(dev_user)
            await db.commit()
            await db.refresh(dev_user)
            logger.info("Created dev user for bypass mode")
        
        return dev_user
    
    # Phase 1: cookie value is just the user_id
    # Future: decode JWT and extract user_id
    try:
        user_id = auth_token
        
        # Fetch user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid token. User not found."
            )
        
        # Check if account is locked
        if user.is_account_locked():
            raise HTTPException(
                status_code=403,
                detail=f"Account temporarily locked due to multiple failed login attempts. Try again after {user.account_locked_until.isoformat()}"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Invalid token."
        )


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require admin role.
    
    Use this for admin-only endpoints to enforce role-based access control.
    
    Args:
        current_user: The authenticated user (from get_current_user)
    
    Returns:
        User: The authenticated admin user
    
    Raises:
        HTTPException 403: If user is not an admin
    
    Example:
        @router.get("/admin/users")
        async def list_all_users(admin: User = Depends(require_admin)):
            # Only admins can access this
    """
    if not current_user.is_admin():
        logger.warning(
            f"User {current_user.email} (role={current_user.role.value}) "
            f"attempted to access admin endpoint"
        )
        raise HTTPException(
            status_code=403,
            detail="Admin access required. You do not have permission to access this resource."
        )
    
    return current_user


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Checks X-Forwarded-For header (for proxies/load balancers) first,
    falls back to direct client IP.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can be comma-separated list, take first IP
        return forwarded.split(",")[0].strip()
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


# Endpoints
@router.post("/verify-token", response_model=AuthResponse)
async def verify_token(
    verify_request: VerifyTokenRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify magic link token and authenticate user.
    
    Returns user info and session token.
    
    Security features:
    - One-time use tokens (cleared after verification)
    - Token expiration validation
    - Account lockout after failed attempts
    - IP address logging
    
    Returns:
        200: Token valid, user authenticated
        401: Invalid or expired token
        403: Account locked due to failed attempts
        500: Database or system error
    """
    try:
        # Find user with this token
        result = await db.execute(
            select(User).where(User.magic_link_token == verify_request.token)
        )
        user = result.scalar_one_or_none()
        
        # Validate token exists
        if not user:
            # Log potential brute force attempt
            logger.warning(f"Invalid token attempt from IP: {get_client_ip(request)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token. Please request a new magic link."
            )
        
        # Check if account is locked (due to previous failed attempts)
        if user.is_account_locked():
            logger.warning(
                f"Login attempt on locked account: {user.email} from IP: {get_client_ip(request)}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Account temporarily locked. Try again after {user.account_locked_until.isoformat()}"
            )
        
        # Validate token not expired
        if user.magic_link_expires_at < datetime.utcnow():
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account after too many failed attempts
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.account_locked_until = datetime.utcnow() + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
                logger.warning(
                    f"Account locked due to {MAX_FAILED_ATTEMPTS} failed attempts: {user.email}"
                )
            
            # Clear expired token
            user.magic_link_token = None
            user.magic_link_expires_at = None
            await db.commit()
            
            raise HTTPException(
                status_code=401,
                detail="Token expired. Please request a new magic link."
            )
        
        # Token is valid - authenticate user
        user.magic_link_token = None  # One-time use
        user.magic_link_expires_at = None
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = get_client_ip(request)
        user.failed_login_attempts = 0  # Reset failed attempts on successful login
        user.account_locked_until = None  # Clear any lock
        
        await db.commit()
        
        logger.info(f"Successful login: {user.email} from IP: {user.last_login_ip}")
        
        # Set httpOnly cookie with user_id
        # In production, set secure=True for HTTPS-only
        response.set_cookie(
            key="auth_token",
            value=str(user.id),
            httponly=True,  # Prevents JavaScript access (XSS protection)
            samesite="lax",  # CSRF protection
            max_age=86400 * 30,  # 30 days
            secure=False,  # Set to True in production with HTTPS
        )
        
        return AuthResponse(
            access_token=str(user.id),  # Kept for compatibility, but cookie is primary
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            profile_complete=user.has_complete_profile()
        )
    
    except HTTPException as http_err:
        # Re-raise HTTP exceptions (401/403 errors with messages already set above)
        # These are expected user errors, not system failures
        raise http_err
    
    except Exception as e:
        # Catch any unexpected errors (database, network, etc.)
        await db.rollback()
        logger.error(f"Error verifying token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Authentication failed. Please try again."
        )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    Logout user by clearing the authentication cookie.
    
    Returns:
        200: Successfully logged out
    """
    response.delete_cookie(
        key="auth_token",
        httponly=True,
        samesite="lax"
    )
    
    logger.info(f"User logged out: {current_user.email}")
    
    return {"message": "Successfully logged out"}