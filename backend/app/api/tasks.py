"""
Tasks API endpoints.
Handles task querying and resume operations.
"""
import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from app.database import get_db
from app.models.application_task import ApplicationTask
from app.models.user import User
from app.api.auth import get_current_user
from app.services.state_machine import transition_task
from app.schemas.task import TaskResponse, ResumeResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Endpoints
@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    state: Optional[str] = Query(None, description="Filter by state (QUEUED, RUNNING, etc.)"),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max tasks to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List application tasks with optional filtering.
    
    Filters:
    - run_id: Tasks for a specific run
    - state: Tasks in a specific state (QUEUED, RUNNING, FAILED, etc.)
    - job_id: Tasks for a specific job
    
    Returns tasks ordered by priority DESC, queued_at ASC (queue order).
    """
    # Build query with filters
    query = select(ApplicationTask)
    filters = []
    
    if run_id:
        filters.append(ApplicationTask.run_id == run_id)
    if state:
        filters.append(ApplicationTask.state == state)
    if job_id:
        filters.append(ApplicationTask.job_id == job_id)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by queue priority (highest priority first, oldest first)
    query = query.order_by(
        ApplicationTask.priority.desc(),
        ApplicationTask.queued_at.asc()
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific task by ID."""
    result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return task


@router.post("/{task_id}/resume", response_model=ResumeResponse)
async def resume_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume a paused or failed task (MANUAL ACTION ONLY).
    
    Valid resume transitions:
    - FAILED → QUEUED (manual retry after 2nd failure - auto-retry already attempted once)
    - NEEDS_AUTH → QUEUED (after user completes login in noVNC)
    - NEEDS_USER → QUEUED (after user provides OTP/answers)
    - EXPIRED → QUEUED (manual retry after approval TTL expired)
    
    Note: Tasks auto-retry ONCE on transient errors. If in FAILED state, it means
    auto-retry already happened and user must manually click Resume to try again.
    
    Resumed tasks get priority boost (100) to jump to front of queue.
    
    Returns 409 if task is in a state that cannot be resumed.
    """
    # Fetch task
    result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    old_state = task.state
    
    # Check if task can be resumed
    resumable_states = ["FAILED", "NEEDS_AUTH", "NEEDS_USER", "EXPIRED"]
    if task.state not in resumable_states:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot resume task in state {task.state}. "
                   f"Only {resumable_states} tasks can be resumed."
        )
    
    # Import TaskState enum
    from app.models.application_task import TaskState
    current_state = TaskState(task.state)
    
    # Transition to QUEUED with priority boost
    try:
        await transition_task(
            db=db,
            task_id=task_id,
            from_state=current_state,
            to_state=TaskState.QUEUED,
            metadata={"resumed_by": "manual_resume", "priority_boost": True}
        )
        
        # Priority boost: jump to front of queue
        task.priority = 100
        await db.commit()
        
        logger.info(f"Task {task_id} resumed: {old_state} → QUEUED (priority=100)")
        
        return ResumeResponse(
            task_id=task_id,
            old_state=old_state,
            new_state="QUEUED",
            priority=100,
            message=f"Task resumed from {old_state} and moved to front of queue"
        )
    
    except ValueError as e:
        # Invalid state transition
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resuming task {task_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to resume task")
