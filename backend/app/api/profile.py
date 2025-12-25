"""
Profile management endpoints.

Provides endpoints for users to manage their profiles including:
- Personal details, professional URLs
- Resume upload/download/delete  
- Mandatory question defaults
- Automation preferences
"""
from datetime import datetime
import logging
import os
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.profile import (
    ProfileUpdateRequest,
    MandatoryQuestionsRequest,
    PreferencesRequest,
    ProfileResponse
)
from app.services.profile import (
    build_profile_response,
    update_user_profile,
    update_mandatory_questions,
    update_preferences,
    attach_resume,
    remove_resume
)
from app.services.resume import (
    get_user_resume_dir,
    validate_resume_file,
    save_resume,
    delete_resume_file
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Endpoints
@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile."""
    await db.refresh(current_user)
    return build_profile_response(current_user)


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile information (partial update)."""
    try:
        update_data = profile_data.model_dump(exclude_unset=True)
        user = await update_user_profile(current_user, update_data, db)
        logger.info(f"Profile updated for user {user.email}")
        return build_profile_response(user)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.put("/profile/questions", response_model=ProfileResponse)
async def update_questions(
    questions: MandatoryQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update mandatory question defaults.
    
    These answers will be used to auto-fill common application questions.
    """
    try:
        questions_dict = questions.model_dump(exclude_unset=True)
        await update_mandatory_questions(current_user, questions_dict, db)
        logger.info(f"Mandatory questions updated for user {current_user.email}")
        return build_profile_response(current_user)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating mandatory questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update mandatory questions")


@router.put("/profile/preferences", response_model=ProfileResponse)
async def update_user_preferences(
    preferences: PreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update automation preferences.
    
    Controls behavior of the job application automation.
    """
    try:
        prefs_dict = preferences.model_dump(exclude_unset=True)
        await update_preferences(current_user, prefs_dict, db)
        logger.info(f"Preferences updated for user {current_user.email}")
        return build_profile_response(current_user)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating preferences: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update preferences")


@router.post("/profile/resume", response_model=ProfileResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload resume file (PDF or DOCX).
    
    Replaces existing resume if one exists.
    Maximum file size: 5MB.
    """
    try:
        validate_resume_file(file)
        resume_path, resume_filename, file_size = save_resume(current_user, file)
        await attach_resume(current_user, str(resume_path), file.filename, file_size, db)
        
        logger.info(f"Resume uploaded for user {current_user.email}: {resume_filename}")
        return build_profile_response(current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading resume: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload resume")


@router.get("/profile/resume")
async def download_resume(
    current_user: User = Depends(get_current_user)
):
    """
    Download user's resume file.
    
    Returns:
        FileResponse: Resume file download
        404: If no resume uploaded
    """
    if not current_user.resume_path:
        raise HTTPException(
            status_code=404,
            detail="No resume uploaded"
        )
    
    resume_path = Path(current_user.resume_path)
    if not resume_path.exists():
        logger.error(f"Resume file not found: {resume_path}")
        raise HTTPException(
            status_code=404,
            detail="Resume file not found"
        )
    
    return FileResponse(
        path=resume_path,
        filename=current_user.resume_filename or "resume.pdf",
        media_type="application/octet-stream"
    )


@router.delete("/profile/resume", response_model=ProfileResponse)
async def delete_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user's resume file.
    
    Returns:
        ProfileResponse: Updated profile with resume removed
        404: If no resume uploaded
    """
    if not current_user.resume_path:
        raise HTTPException(status_code=404, detail="No resume uploaded")
    
    try:
        delete_resume_file(current_user.resume_path)
        await remove_resume(current_user, db)
        
        logger.info(f"Resume deleted for user {current_user.email}")
        return build_profile_response(current_user)
    except Exception as e:
        logger.error(f"Error deleting resume: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete resume")
