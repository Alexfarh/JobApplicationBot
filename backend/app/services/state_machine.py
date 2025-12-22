"""
State machine for application tasks.
ALL state transitions must go through this module.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.application_task import ApplicationTask, TaskState


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
    TaskState.PENDING_APPROVAL: [TaskState.APPROVED, TaskState.EXPIRED],
    TaskState.APPROVED: [TaskState.RUNNING, TaskState.EXPIRED],  # Worker interrupts to process; can expire if session lost
    TaskState.FAILED: [TaskState.QUEUED],  # Manual resume
    TaskState.SUBMITTED: [],  # Terminal state
    TaskState.EXPIRED: [],  # Terminal state
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


async def transition_task(
    db: AsyncSession,
    task_id: str,
    to_state: TaskState,
    metadata: Optional[Dict[str, Any]] = None
) -> ApplicationTask:
    """
    Transition a task to a new state with validation.
    
    Args:
        db: Database session
        task_id: ID of the task to transition
        to_state: Target state
        metadata: Optional metadata about the transition (error info, etc.)
    
    Returns:
        Updated ApplicationTask
        
    Raises:
        InvalidTransitionError: If transition is not allowed
    """
    # Fetch the task
    result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    from_state = TaskState(task.state)
    
    # Validate transition
    if to_state not in ALLOWED_TRANSITIONS.get(from_state, []):
        raise InvalidTransitionError(
            f"Invalid transition from {from_state.value} to {to_state.value}"
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
        task.started_at = datetime.utcnow()
        task.attempt_count += 1
    
    await db.commit()
    await db.refresh(task)
    
    # Log transition
    print(f"[STATE_MACHINE] Task {task_id}: {from_state.value} → {to_state.value}")
    
    return task


async def can_transition(from_state: TaskState, to_state: TaskState) -> bool:
    """Check if a transition is allowed without modifying the database"""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, [])
