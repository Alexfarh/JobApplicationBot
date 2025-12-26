"""Resume file management service."""
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.models.user import User

logger = logging.getLogger(__name__)

# Configuration
RESUME_DIR = Path("/data/resumes")
MAX_RESUME_SIZE_MB = 5
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def get_user_resume_dir(user_id: str) -> Path:
    """Get the resume directory for a specific user."""
    return RESUME_DIR / str(user_id)


def validate_resume_file(file: UploadFile) -> None:
    """
    Validate resume file upload.
    
    Raises:
        HTTPException 400: If file is invalid
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if hasattr(file, 'size') and file.size:
        max_size = MAX_RESUME_SIZE_MB * 1024 * 1024
        if file.size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_RESUME_SIZE_MB}MB"
            )


def save_resume(user: User, file: UploadFile):
    """
    (Deprecated) No longer used. Resume is now stored in DB.
    """
    raise NotImplementedError("Resume disk storage is deprecated. Store resume in DB.")


def delete_resume_file(file_path: str) -> None:
    """Delete resume file from disk."""
    try:
        path = Path(file_path)
        if path.exists():
            os.remove(path)
    except Exception as e:
        logger.warning(f"Failed to delete resume file {file_path}: {str(e)}")
