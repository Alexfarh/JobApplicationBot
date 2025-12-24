"""
Queue management service for application tasks.
Handles dequeuing with SELECT FOR UPDATE SKIP LOCKED.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.application_task import ApplicationTask, TaskState
from app.services.state_machine import transition_task

logger = logging.getLogger(__name__)


# Priority levels for queue ordering
PRIORITY_APPROVED = 200   # Highest - approved tasks (time-sensitive, session expires)
PRIORITY_RESUMED = 100    # High - manually resumed tasks (user took action)
PRIORITY_NORMAL = 50      # Normal - regular queue tasks


async def dequeue_next_task(
    db: AsyncSession,
    run_id: str
) -> Optional[ApplicationTask]:
    """
    Dequeue the next task from the queue for a given run.
    Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions.
    
    Args:
        db: Database session
        run_id: ID of the application run
        
    Returns:
        ApplicationTask if found, None if queue is empty
    """
    # Critical queue dequeue query
    result = await db.execute(
        select(ApplicationTask)
        .where(
            and_(
                ApplicationTask.run_id == run_id,
                ApplicationTask.state == TaskState.QUEUED.value
            )
        )
        .order_by(
            ApplicationTask.priority.desc(),
            ApplicationTask.queued_at.asc()
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    
    task = result.scalar_one_or_none()
    return task


async def recover_stuck_tasks(
    db: AsyncSession,
    timeout_minutes: int = 15,
    max_attempts: int = 3
) -> int:
    """
    Find tasks stuck in RUNNING state and move them back to QUEUED or FAILED.
    This handles cases where the worker crashed or timed out.
    
    Args:
        db: Database session
        timeout_minutes: How long before a RUNNING task is considered stuck
        max_attempts: Maximum retry attempts before marking as FAILED
        
    Returns:
        Number of tasks recovered
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    # Find stuck tasks
    result = await db.execute(
        select(ApplicationTask)
        .where(
            and_(
                ApplicationTask.state == TaskState.RUNNING.value,
                ApplicationTask.started_at < cutoff_time
            )
        )
    )
    
    stuck_tasks = result.scalars().all()
    
    # Recover or fail based on attempt count
    # Use transition_task to ensure state machine rules are followed
    for task in stuck_tasks:
        if task.attempt_count >= max_attempts:
            # Exceeded max attempts - mark as FAILED
            await transition_task(
                db,
                str(task.id),
                TaskState.RUNNING,  # from_state
                TaskState.FAILED,   # to_state
                metadata={
                    "error_code": "MAX_ATTEMPTS_EXCEEDED",
                    "error_message": f"Task stuck in RUNNING state after {task.attempt_count} attempts"
                }
            )
            logger.warning(f"Task {task.id} FAILED after {task.attempt_count} attempts")
        else:
            # Still have attempts left - recover to QUEUED
            await transition_task(db, str(task.id), TaskState.RUNNING, TaskState.QUEUED)
            logger.info(f"Recovered stuck task {task.id} (attempt {task.attempt_count}/{max_attempts})")
    
    return len(stuck_tasks)


async def resume_task(
    db: AsyncSession,
    task_id: str
) -> ApplicationTask:
    """
    Resume a failed or paused task with priority boost.
    
    Args:
        db: Database session
        task_id: ID of the task to resume
        
    Returns:
        Updated ApplicationTask
    """
    result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    # Determine current state for optimistic locking
    current_state = TaskState(task.state)
    
    # Use transition_task to ensure state machine rules are followed
    # Priority boost and timestamp update happens in state machine
    updated_task = await transition_task(db, task_id, current_state, TaskState.QUEUED)
    
    # Manual resume gets extra priority boost (state machine handles NEEDS_AUTH/NEEDS_USER boost)
    updated_task.priority = PRIORITY_RESUMED
    updated_task.queued_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(updated_task)
    
    logger.info(f"Resumed task {task_id} with priority boost")
    
    return updated_task
