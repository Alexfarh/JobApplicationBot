"""
State machine for application tasks.
ALL state transitions must go through this module.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.application_task import ApplicationTask, TaskState
from app.models.job_posting import JobPosting

# Configure logger
logger = logging.getLogger(__name__)


# Define allowed state transitions
ALLOWED_TRANSITIONS: Dict[TaskState, list[TaskState]] = {
    TaskState.QUEUED: [TaskState.RUNNING],
    TaskState.RUNNING: [
        TaskState.NEEDS_AUTH,
        TaskState.NEEDS_USER,
        TaskState.PENDING_APPROVAL,
        TaskState.SUBMITTED,
        TaskState.FAILED,
        TaskState.EXPIRED,
        TaskState.QUEUED,  # For stuck-task recovery
    ],
    TaskState.NEEDS_AUTH: [TaskState.QUEUED],  # After user completes auth
    TaskState.NEEDS_USER: [TaskState.QUEUED],  # After user provides input
    TaskState.PENDING_APPROVAL: [TaskState.APPROVED, TaskState.EXPIRED, TaskState.REJECTED],
    TaskState.APPROVED: [TaskState.RUNNING, TaskState.EXPIRED],  # Worker interrupts to process; can expire if session lost
    TaskState.FAILED: [TaskState.QUEUED],  # Manual resume only (after auto-retry exhausted)
    TaskState.SUBMITTED: [],  # Terminal state
    TaskState.REJECTED: [],  # Terminal state (user explicitly rejected)
    TaskState.EXPIRED: [TaskState.QUEUED],  # Manual resume for expired approvals
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


async def transition_task(
    db: AsyncSession,
    task_id: str,
    from_state: Optional[TaskState],
    to_state: TaskState,
    metadata: Optional[Dict[str, Any]] = None
) -> ApplicationTask:
    """
    Transition a task to a new state with validation.
    
    Args:
        db: Database session
        task_id: ID of the task to transition
        from_state: Expected current state (for optimistic locking). None means skip validation (initial state).
        to_state: Target state
        metadata: Optional metadata about the transition (error info, etc.)
    
    Returns:
        Updated ApplicationTask
        
    Raises:
        InvalidTransitionError: If transition is not allowed
        ValueError: If task not found or from_state doesn't match
    """
    # Fetch the task
    result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    current_state = TaskState(task.state)
    
    # Optimistic locking: verify the task is still in the expected state
    # Skip validation if from_state is None (initial state / no lock needed)
    if from_state is not None and current_state != from_state:
        raise ValueError(
            f"Task {task_id} is in state {current_state.value}, expected {from_state.value}"
        )
    
    # Use current_state for transition validation
    transition_from = from_state if from_state is not None else current_state
    
    # Validate transition
    if to_state not in ALLOWED_TRANSITIONS.get(transition_from, []):
        raise InvalidTransitionError(
            f"Invalid transition from {transition_from.value} to {to_state.value}"
        )
    
    # Update task state
    task.state = to_state.value
    task.last_state_change_at = datetime.utcnow()
    
    # Handle metadata
    if metadata:
        if "error_code" in metadata:
            task.last_error_code = metadata["error_code"]
        if "error_message" in metadata:
            task.last_error_message = metadata["error_message"]
    
    # State-specific updates
    if to_state == TaskState.RUNNING:
        if task.started_at is None:
            task.started_at = datetime.utcnow()
        task.attempt_count += 1
    
    # Auto-retry logic: First failure goes back to QUEUED, second failure is terminal
    if to_state == TaskState.FAILED:
        if task.attempt_count < 2:
            # First failure - auto-retry once with boosted priority for immediate retry
            task.state = TaskState.QUEUED.value
            task.priority = 100  # Boosted priority for immediate retry
        # else: Second failure - stays in FAILED (terminal)
    
    # Priority boost when resuming to QUEUED from user-unblocked states
    # This pushes the task to front of queue and spawns subprocess
    if to_state == TaskState.QUEUED and from_state in [
        TaskState.NEEDS_AUTH,
        TaskState.NEEDS_USER,
    ]:
        task.priority = 100  # Boosted priority (default is 50)
        # TODO: Spawn subprocess worker for immediate processing (V1: max 1 subprocess)
        # This allows unblocked task to run concurrently with main worker
    
    # Priority boost for approved tasks transitioning to RUNNING
    # Highest priority (200) because approval has TTL and session may expire
    if to_state == TaskState.RUNNING and from_state == TaskState.APPROVED:
        task.priority = 200  # Highest priority - time-sensitive
    
    # Mark job as applied only on successful submission
    if to_state == TaskState.SUBMITTED:
        await _mark_job_as_applied(db, task.job_id)
    
    await db.commit()
    await db.refresh(task)
    
    # Log transition with metadata
    log_data = {
        "task_id": str(task_id),
        "from_state": transition_from.value,
        "to_state": to_state.value,
        "attempt_count": task.attempt_count,
        "priority": task.priority,
    }
    if metadata:
        log_data["metadata"] = metadata
    
    logger.info(f"Task state transition: {transition_from.value} → {to_state.value}", extra=log_data)
    
    return task


async def can_transition(from_state: TaskState, to_state: TaskState) -> bool:
    """Check if a transition is allowed without modifying the database"""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, [])


async def _mark_job_as_applied(db: AsyncSession, job_id: int) -> None:
    """
    Mark a job posting as successfully applied to.
    Only called when a task transitions to SUBMITTED state.
    This ensures EXPIRED tasks don't prevent future reapplications.
    """
    result = await db.execute(
        select(JobPosting).where(JobPosting.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if job:
        job.has_been_applied_to = True
        job.last_applied_at = datetime.utcnow()
        # Note: commit handled by caller (transition_task)
