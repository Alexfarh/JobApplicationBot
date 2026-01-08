"""Profile management business logic."""
from datetime import datetime
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
import pdfplumber
import io

from app.models.user import User
from app.schemas.profile import (
    ProfileResponse,
    ResumeDataSchema,
    ExperienceSchema,
    EducationSchema,
)
from app.services.resume_extraction import ResumeExtractor


def build_profile_response(user: User) -> ProfileResponse:
    """Build ProfileResponse from User model, extracting resume data if available."""
    resume_data = None
    
    # Extract resume data if resume has been uploaded
    if user.resume_data:
        try:
            # Convert binary resume data to text
            resume_bytes = io.BytesIO(user.resume_data)
            
            # Try PDF extraction first
            try:
                with pdfplumber.open(resume_bytes) as pdf:
                    text = '\n'.join(page.extract_text() for page in pdf.pages)
            except:
                # If not PDF, treat as text
                text = user.resume_data.decode('utf-8', errors='ignore')
            
            # Extract structured data
            extracted = ResumeExtractor.parse(text)
            
            # Convert to schema format
            resume_data = ResumeDataSchema(
                name=extracted.name,
                email=extracted.email,
                phone=extracted.phone,
                github=extracted.github,
                linkedin=extracted.linkedin,
                portfolio=extracted.portfolio,
                skills=extracted.skills,
                experience=[
                    ExperienceSchema(
                        company=exp.company,
                        title=exp.title,
                        start_date=exp.start_date,
                        end_date=exp.end_date,
                        duration_years=exp.duration_years,
                        description=exp.description,
                    )
                    for exp in extracted.experience
                ],
                education=[
                    EducationSchema(
                        institution=edu.institution,
                        degree=edu.degree,
                        field=edu.field,
                        graduation_year=edu.graduation_year,
                    )
                    for edu in extracted.education
                ],
                projects=extracted.projects,
                total_experience_years=extracted.total_experience_years,
                seniority_level=extracted.seniority_level,
            )
        except Exception as e:
            # Log error but don't fail - just return profile without extracted data
            print(f"Error extracting resume data: {e}")
            resume_data = None
    
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
        resume_uploaded=user.resume_data is not None,
        resume_filename=user.resume_filename,
        resume_uploaded_at=user.resume_uploaded_at,
        resume_size_bytes=user.resume_size_bytes,
        resume_data=resume_data,
        internship_only=user.internship_only,
        preferred_job_types=user.preferred_job_types or [],
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


async def attach_resume(user: User, resume_bytes: bytes, filename: str, file_size: int, db: AsyncSession) -> User:
    """Attach resume info to user profile (DB storage)."""
    import logging
    logger = logging.getLogger(__name__)
    user.resume_data = resume_bytes
    user.resume_filename = filename
    user.resume_uploaded_at = datetime.utcnow()
    user.resume_size_bytes = file_size
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    logger.info(f"[DEBUG] After attach_resume: resume_data is {'set' if user.resume_data else 'None'}, resume_filename={user.resume_filename}")
    return user


async def remove_resume(user: User, db: AsyncSession) -> User:
    """Remove resume info from user profile (DB storage)."""
    user.resume_data = None
    user.resume_filename = None
    user.resume_uploaded_at = None
    user.resume_size_bytes = None
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user
