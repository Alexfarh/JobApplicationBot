"""Profile management business logic."""
from datetime import datetime
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.profile import ProfileResponse


def build_profile_response(user: User) -> ProfileResponse:
    """Build ProfileResponse from User model."""
    return ProfileResponse(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        full_name=user.full_name,
        phone=user.phone,
        address_street=user.address_street,
        address_city=user.address_city,
        address_state=user.address_state,
        address_zip=user.address_zip,
        address_country=user.address_country,
        linkedin_url=user.linkedin_url,
        github_url=user.github_url,
        portfolio_url=user.portfolio_url,
        resume_uploaded=user.resume_path is not None,
        resume_filename=user.resume_filename,
        resume_uploaded_at=user.resume_uploaded_at,
        resume_size_bytes=user.resume_size_bytes,
        mandatory_questions=user.mandatory_questions,
        preferences=user.preferences,
        profile_complete=user.has_complete_profile(),
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at
    )


async def update_user_profile(user: User, update_data: dict, db: AsyncSession) -> User:
    """Update user profile fields."""
    for field, value in update_data.items():
        # Convert URL strings if needed (Pydantic already validated them)
        if field in ['linkedin_url', 'github_url', 'portfolio_url'] and value is not None:
            value = str(value)
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def update_mandatory_questions(user: User, questions_dict: dict, db: AsyncSession) -> User:
    """Update user's mandatory questions."""
    if user.mandatory_questions is None:
        user.mandatory_questions = {}
    
    user.mandatory_questions.update(questions_dict)
    # Flag the field as modified so SQLAlchemy detects the change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, "mandatory_questions")
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def update_preferences(user: User, prefs_dict: dict, db: AsyncSession) -> User:
    """Update user's automation preferences."""
    if user.preferences is None:
        user.preferences = {
            "optimistic_mode": True,
            "require_approval": True,
            "preferred_platforms": ["greenhouse"]
        }
    
    user.preferences.update(prefs_dict)
    # Flag the field as modified so SQLAlchemy detects the change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, "preferences")
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def attach_resume(user: User, file_path: str, filename: str, file_size: int, db: AsyncSession) -> User:
    """Attach resume info to user profile."""
    user.resume_path = file_path
    user.resume_filename = filename
    user.resume_uploaded_at = datetime.utcnow()
    user.resume_size_bytes = file_size
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def remove_resume(user: User, db: AsyncSession) -> User:
    """Remove resume info from user profile."""
    user.resume_path = None
    user.resume_filename = None
    user.resume_uploaded_at = None
    user.resume_size_bytes = None
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user
