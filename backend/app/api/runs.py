"""
Application Run endpoints.

A run represents a batch of job applications to process.
"""
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime
import logging

from app.database import get_db
from app.models.application_run import ApplicationRun, RunStatus
from app.models.application_task import ApplicationTask
from app.models.user import User
from app.services.run_queue import start_next_run, complete_run, get_active_run
from app.api.auth import get_current_user
from app.schemas.run import CreateRunRequest, RunResponse, RunListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependencies
async def require_complete_profile(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that ensures user has a complete profile before creating runs.
    
    A complete profile requires:
    - Full name
    - Phone number
    - City, state, country
    - Uploaded resume
    
    Args:
        current_user: Authenticated user from get_current_user dependency
        
    Returns:
        User object if profile is complete
        
    Raises:
        HTTPException 403: Profile is incomplete
    """
    if not current_user.has_complete_profile():
        missing_fields = []
        
        if not current_user.full_name:
            missing_fields.append("full name")
        if not current_user.email:
            missing_fields.append("email")
        if not current_user.phone:
            missing_fields.append("phone number")
        if not current_user.resume_data:
            missing_fields.append("resume")
        
        # Check mandatory questions
        if not current_user.mandatory_questions:
            missing_fields.append("mandatory questions")
        else:
            critical_questions = ['work_authorization', 'veteran_status', 'disability_status']
            missing_questions = []
            for question in critical_questions:
                if question not in current_user.mandatory_questions or not current_user.mandatory_questions[question]:
                    missing_questions.append(question)
            if missing_questions:
                missing_fields.append(f"mandatory questions ({', '.join(missing_questions)})")
        
        logger.warning(
            f"User {current_user.email} attempted to create run with incomplete profile. "
            f"Missing: {', '.join(missing_fields)}"
        )
        
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Complete your profile before creating a run",
                "missing_fields": missing_fields,
                "profile_url": "/profile"  # Frontend can redirect here
            }
        )
    
    return current_user

# Helper functions
async def get_run_by_id(run_id: str, user_id: str, db: AsyncSession) -> ApplicationRun:
    """
    Get a run by ID and verify user owns it.
    
    Args:
        run_id: Run UUID as string
        user_id: User UUID as string
        db: Database session
        
    Returns:
        ApplicationRun object if found and owned by user
        
    Raises:
        HTTPException 404: Run not found
        HTTPException 403: User doesn't own the run
    """
    # First check if run exists at all
    result = await db.execute(
        select(ApplicationRun)
        .where(ApplicationRun.id == UUID(run_id))
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail="Run not found. The run ID may be invalid."
        )
    
    # Then check if user owns it
    if str(run.user_id) != user_id:
        # Log for debugging (server-side only, not sent to client)
        logger.warning(f"Access denied: User {user_id} tried to access run {run_id} owned by {run.user_id}")
        raise HTTPException(
            status_code=403,
            detail="Access denied. You don't have permission to access this run."
        )
    
    return run

async def get_run_with_task_counts(run: ApplicationRun, db: AsyncSession) -> "RunResponse":
    """
    Convert an ApplicationRun to RunResponse with task counts.
    
    Args:
        run: The ApplicationRun database object
        db: Database session
        
    Returns:
        RunResponse with all task counts populated
    """
    # Count tasks by state
    task_result = await db.execute(
        select(ApplicationTask)
        .where(ApplicationTask.run_id == run.id)
    )
    tasks = task_result.scalars().all()
    
    return RunResponse(
        id=str(run.id),
        user_id=str(run.user_id),
        name=run.name,
        description=run.description,
        status=run.status,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        updated_at=run.updated_at,
        total_tasks=len(tasks),
        queued_tasks=sum(1 for t in tasks if t.state == "QUEUED"),
        running_tasks=sum(1 for t in tasks if t.state == "RUNNING"),
        submitted_tasks=sum(1 for t in tasks if t.state == "SUBMITTED"),
        failed_tasks=sum(1 for t in tasks if t.state == "FAILED"),
        rejected_tasks=sum(1 for t in tasks if t.state == "REJECTED"),
    )

# Endpoints
@router.post("/", response_model=RunResponse, status_code=201)
async def create_run(
    request: CreateRunRequest,
    current_user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new application run.
    
    A run is a batch of job applications to process.
    After creating, add jobs via POST /runs/{run_id}/jobs
    
    V1 Constraint: Only ONE run can have status='running' at a time.
    New runs default to 'queued' status.
    
    Requires: Complete user profile (name, phone, address, resume)
    """
    try:
        user_id = str(current_user.id)
        
        # V1: Check if user already has a running run
        result = await db.execute(
            select(ApplicationRun)
            .where(
                ApplicationRun.user_id == UUID(user_id),
                ApplicationRun.status == RunStatus.RUNNING.value
            )
        )
        existing_running_run = result.scalar_one_or_none()
        
        if existing_running_run:
            logger.warning(
                f"User {user_id} attempted to create run while run {existing_running_run.id} is still running"
            )
            raise HTTPException(
                status_code=409,
                detail=f"You already have an active run: '{existing_running_run.name or str(existing_running_run.id)}'. "
                       f"Complete or stop it before starting a new one."
            )
        
        run = ApplicationRun(
            user_id=UUID(user_id),
            name=request.name,
            description=request.description
            # status defaults to "queued" from model
        )
        
        db.add(run)
        await db.commit()
        await db.refresh(run)
        
        return RunResponse(
            id=str(run.id),
            user_id=str(run.user_id),
            name=run.name,
            description=run.description,
            status=run.status,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            updated_at=run.updated_at,
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating run: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create run. Please try again."
        )

@router.get("/", response_model=RunListResponse)
async def list_runs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all runs for a user, sorted by most recent first.
    """
    try:
        user_id = str(current_user.id)
        result = await db.execute(
            select(ApplicationRun)
            .where(ApplicationRun.user_id == UUID(user_id))
            .order_by(ApplicationRun.created_at.desc())
        )
        runs = result.scalars().all()
        
        # Get task counts for each run using helper function
        run_responses = []
        for run in runs:
            run_response = await get_run_with_task_counts(run, db)
            run_responses.append(run_response)
        
        return RunListResponse(
            runs=run_responses,
            total=len(run_responses)
        )
    
    except Exception as e:
        logger.error(f"Error listing runs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch runs. Please try again."
        )

@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific run.
    """
    try:
        user_id = str(current_user.id)
        # Get run and verify ownership
        run = await get_run_by_id(run_id, user_id, db)
        
        # Get task counts using helper function
        return await get_run_with_task_counts(run, db)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error fetching run: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch run details. Please try again."
        )

@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a run and all its associated tasks.
    
    Note: Tasks will be deleted via CASCADE constraint.
    """
    try:
        user_id = str(current_user.id)
        # Get run and verify ownership
        run = await get_run_by_id(run_id, user_id, db)
        
        await db.delete(run)
        await db.commit()
        
        return None  # 204 No Content
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting run: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete run. Please try again."
        )


@router.post("/{run_id}/start", response_model=RunResponse)
async def start_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start a queued run (transition from 'queued' to 'running').
    
    V1 Constraint: Only ONE run can be running at a time.
    If another run is already running, this will fail with 409 Conflict.
    """
    try:
        user_id = str(current_user.id)
        # Get run and verify ownership
        run = await get_run_by_id(run_id, user_id, db)
        
        # Check if already running
        if run.status == RunStatus.RUNNING.value:
            raise HTTPException(
                status_code=400,
                detail="Run is already running."
            )
        
        # Check if already completed
        if run.status == RunStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400,
                detail="Cannot start a completed run."
            )
        
        # Check if another run is already running
        active_run = await get_active_run(db, user_id)
        if active_run and str(active_run.id) != run_id:
            raise HTTPException(
                status_code=409,
                detail=f"Another run is already active: '{active_run.name or str(active_run.id)}'. "
                       f"Complete it before starting this one."
            )
        
        # Start the run
        run.status = RunStatus.RUNNING.value
        run.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(run)
        
        logger.info(f"Started run {run_id} ('{run.name}')")
        
        return await get_run_with_task_counts(run, db)
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting run: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to start run. Please try again."
        )


@router.post("/{run_id}/complete", response_model=RunResponse)
async def mark_run_complete(
    run_id: str,
    auto_start_next: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a run as completed and optionally start the next queued run.
    
    Args:
        run_id: Run UUID
        auto_start_next: If True, automatically start next queued run (default: True)
    """
    try:
        user_id = str(current_user.id)
        # Get run and verify ownership
        run = await get_run_by_id(run_id, user_id, db)
        
        # Mark as completed (and optionally start next run)
        next_run = await complete_run(db, run_id, auto_start_next=auto_start_next)
        
        # Return the completed run
        await db.refresh(run)
        return await get_run_with_task_counts(run, db)
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing run: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to complete run. Please try again."
        )
