"""
Run queue management service.
Handles transitioning runs between queued -> running -> completed.
V1: Only ONE run can have status='running' at a time.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from app.models.application_run import ApplicationRun, RunStatus

logger = logging.getLogger(__name__)


async def get_active_run(db: AsyncSession, user_id: str) -> Optional[ApplicationRun]:
    """
    Get the currently running run for a user.
    
    Args:
        db: Database session
        user_id: User UUID as string
        
    Returns:
        ApplicationRun with status='running' if exists, None otherwise
    """
    result = await db.execute(
        select(ApplicationRun)
        .where(
            and_(
                ApplicationRun.user_id == user_id,
                ApplicationRun.status == RunStatus.RUNNING.value
            )
        )
    )
    return result.scalar_one_or_none()


async def start_next_run(db: AsyncSession, user_id: str) -> Optional[ApplicationRun]:
    """
    Start the next queued run for a user.
    Transitions oldest queued run to 'running' status.
    
    Args:
        db: Database session
        user_id: User UUID as string
        
    Returns:
        ApplicationRun that was started, or None if no queued runs exist
        
    Raises:
        RuntimeError: If a run is already running (should check first)
    """
    # Safety check: ensure no run is currently running
    active_run = await get_active_run(db, user_id)
    if active_run:
        raise RuntimeError(
            f"Cannot start new run: Run {active_run.id} is already running. "
            f"Complete it first."
        )
    
    # Get oldest queued run (FIFO)
    result = await db.execute(
        select(ApplicationRun)
        .where(
            and_(
                ApplicationRun.user_id == user_id,
                ApplicationRun.status == RunStatus.QUEUED.value
            )
        )
        .order_by(ApplicationRun.created_at.asc())
        .limit(1)
    )
    
    next_run = result.scalar_one_or_none()
    
    if next_run:
        # Transition to running
        next_run.status = RunStatus.RUNNING.value
        next_run.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(next_run)
        
        logger.info(
            f"Started run {next_run.id} ('{next_run.name}') for user {user_id}"
        )
    
    return next_run


async def complete_run(
    db: AsyncSession,
    run_id: str,
    auto_start_next: bool = True
) -> Optional[ApplicationRun]:
    """
    Mark a run as completed and optionally start the next queued run.
    
    Args:
        db: Database session
        run_id: Run UUID as string
        auto_start_next: If True, automatically start next queued run
        
    Returns:
        Next run that was started (if auto_start_next=True), or None
    """
    # Get the run
    result = await db.execute(
        select(ApplicationRun).where(ApplicationRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise ValueError(f"Run {run_id} not found")
    
    # Mark as completed
    run.status = RunStatus.COMPLETED.value
    run.completed_at = datetime.utcnow()
    await db.commit()
    
    logger.info(f"Completed run {run_id} ('{run.name}')")
    
    # Optionally start next run
    next_run = None
    if auto_start_next:
        next_run = await start_next_run(db, str(run.user_id))
        if next_run:
            logger.info(f"Auto-started next run: {next_run.id} ('{next_run.name}')")
    
    return next_run


async def list_queued_runs(db: AsyncSession, user_id: str) -> list[ApplicationRun]:
    """
    List all queued runs for a user, ordered by creation time (FIFO).
    
    Args:
        db: Database session
        user_id: User UUID as string
        
    Returns:
        List of ApplicationRun objects with status='queued'
    """
    result = await db.execute(
        select(ApplicationRun)
        .where(
            and_(
                ApplicationRun.user_id == user_id,
                ApplicationRun.status == RunStatus.QUEUED.value
            )
        )
        .order_by(ApplicationRun.created_at.asc())
    )
    
    return list(result.scalars().all())
