"""
Tests for queue service (dequeue, stuck task recovery, resume).
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.application_run import ApplicationRun
from app.models.job_posting import JobPosting
from app.models.application_task import ApplicationTask, TaskState
from app.services.queue import (
    dequeue_next_task,
    recover_stuck_tasks,
    resume_task,
    PRIORITY_NORMAL,
    PRIORITY_RESUMED,
    PRIORITY_APPROVED
)


@pytest_asyncio.fixture
async def user(db: AsyncSession):
    """Create a test user."""
    user = User(
        email="test@example.com",
        magic_link_token="test-magic-link-token",
        magic_link_expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def application_run(db: AsyncSession, user: User):
    """Create a test application run with status='running'."""
    run = ApplicationRun(
        user_id=str(user.id),
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@pytest_asyncio.fixture
async def job_posting(db: AsyncSession):
    """Create a test job posting."""
    job = JobPosting(
        job_title="Software Engineer",
        company_name="Test Corp",
        job_url="https://example.com/job/123",
        apply_url="https://example.com/apply",
        has_been_applied_to=False
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


# ============================================================
# DEQUEUE TESTS
# ============================================================

@pytest.mark.asyncio
async def test_dequeue_empty_queue(db: AsyncSession, application_run: ApplicationRun):
    """Test dequeuing from an empty queue returns None."""
    task = await dequeue_next_task(db, str(application_run.id))
    assert task is None


@pytest.mark.asyncio
async def test_dequeue_orders_by_priority_desc(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that higher priority tasks are dequeued first."""
    # Create 3 tasks with different priorities
    task_normal = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=datetime.utcnow()
    )
    task_resumed = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_2",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_RESUMED,
        queued_at=datetime.utcnow()
    )
    task_approved = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_3",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_APPROVED,
        queued_at=datetime.utcnow()
    )
    
    db.add_all([task_normal, task_resumed, task_approved])
    await db.commit()
    
    # First dequeue should get highest priority (APPROVED = 200)
    first = await dequeue_next_task(db, str(application_run.id))
    assert first.priority == PRIORITY_APPROVED
    
    # Mark as RUNNING and dequeue again
    first.state = TaskState.RUNNING.value
    await db.commit()
    
    # Second dequeue should get next highest (RESUMED = 100)
    second = await dequeue_next_task(db, str(application_run.id))
    assert second.priority == PRIORITY_RESUMED
    
    # Mark as RUNNING and dequeue again
    second.state = TaskState.RUNNING.value
    await db.commit()
    
    # Third dequeue should get lowest (NORMAL = 50)
    third = await dequeue_next_task(db, str(application_run.id))
    assert third.priority == PRIORITY_NORMAL


@pytest.mark.asyncio
async def test_dequeue_orders_by_queued_at_asc_for_same_priority(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that tasks with same priority are dequeued FIFO (oldest first)."""
    now = datetime.utcnow()
    
    # Create 3 tasks with same priority but different timestamps
    task_oldest = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_1",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=now - timedelta(minutes=10)
    )
    task_middle = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_2",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=now - timedelta(minutes=5)
    )
    task_newest = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_3",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=now
    )
    
    db.add_all([task_newest, task_middle, task_oldest])  # Add in random order
    await db.commit()
    
    # Dequeue should get oldest first
    first = await dequeue_next_task(db, str(application_run.id))
    assert first.job_id == str(job_posting.id) + "_1"
    
    first.state = TaskState.RUNNING.value
    await db.commit()
    
    second = await dequeue_next_task(db, str(application_run.id))
    assert second.job_id == str(job_posting.id) + "_2"
    
    second.state = TaskState.RUNNING.value
    await db.commit()
    
    third = await dequeue_next_task(db, str(application_run.id))
    assert third.job_id == str(job_posting.id) + "_3"


@pytest.mark.asyncio
async def test_dequeue_only_returns_queued_state(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that only QUEUED tasks are returned (not RUNNING, FAILED, etc.)."""
    # Create tasks in various states
    task_queued = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_queued",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=datetime.utcnow()
    )
    task_running = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_running",
        state=TaskState.RUNNING.value,
        priority=PRIORITY_NORMAL,
        queued_at=datetime.utcnow()
    )
    task_failed = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_failed",
        state=TaskState.FAILED.value,
        priority=PRIORITY_NORMAL,
        queued_at=datetime.utcnow()
    )
    
    db.add_all([task_queued, task_running, task_failed])
    await db.commit()
    
    # Should only return QUEUED task
    task = await dequeue_next_task(db, str(application_run.id))
    assert task.state == TaskState.QUEUED.value
    assert task.job_id == str(job_posting.id) + "_queued"
    
    # Mark as RUNNING and dequeue again - should return None
    task.state = TaskState.RUNNING.value
    await db.commit()
    
    second_task = await dequeue_next_task(db, str(application_run.id))
    assert second_task is None


@pytest.mark.asyncio
async def test_dequeue_filters_by_run_id(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting,
    user: User
):
    """Test that dequeue only returns tasks for the specified run."""
    # Create another run
    other_run = ApplicationRun(
        user_id=str(user.id),
        status="active",
        started_at=datetime.utcnow()
    )
    db.add(other_run)
    await db.commit()
    await db.refresh(other_run)
    
    # Create task for other run
    other_task = ApplicationTask(
        run_id=str(other_run.id),
        job_id=str(job_posting.id) + "_other",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=datetime.utcnow()
    )
    
    # Create task for target run
    target_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_target",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=datetime.utcnow()
    )
    
    db.add_all([other_task, target_task])
    await db.commit()
    
    # Dequeue for application_run should only get target_task
    task = await dequeue_next_task(db, str(application_run.id))
    assert task.run_id == str(application_run.id)
    assert task.job_id == str(job_posting.id) + "_target"


# ============================================================
# STUCK TASK RECOVERY TESTS
# ============================================================

@pytest.mark.asyncio
async def test_recover_stuck_tasks_moves_to_queued(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that stuck tasks with attempts < max are moved back to QUEUED."""
    # Create a task stuck in RUNNING for 20 minutes (attempt 1)
    stuck_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.RUNNING.value,
        priority=PRIORITY_NORMAL,
        started_at=datetime.utcnow() - timedelta(minutes=20),
        attempt_count=1
    )
    db.add(stuck_task)
    await db.commit()
    
    # Run recovery with 15 minute timeout
    recovered_count = await recover_stuck_tasks(db, timeout_minutes=15, max_attempts=3)
    
    assert recovered_count == 1
    
    # Check task is now QUEUED
    await db.refresh(stuck_task)
    assert stuck_task.state == TaskState.QUEUED.value


@pytest.mark.asyncio
async def test_recover_stuck_tasks_moves_to_failed_after_max_attempts(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that stuck tasks with attempts >= max are marked FAILED."""
    # Create a task stuck in RUNNING with max attempts reached
    stuck_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.RUNNING.value,
        priority=PRIORITY_NORMAL,
        started_at=datetime.utcnow() - timedelta(minutes=20),
        attempt_count=3
    )
    db.add(stuck_task)
    await db.commit()
    
    # Run recovery with 15 minute timeout, max 3 attempts
    recovered_count = await recover_stuck_tasks(db, timeout_minutes=15, max_attempts=3)
    
    assert recovered_count == 1
    
    # Check task is now FAILED
    await db.refresh(stuck_task)
    assert stuck_task.state == TaskState.FAILED.value


@pytest.mark.asyncio
async def test_recover_stuck_tasks_ignores_recent_running_tasks(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that tasks running within timeout window are not recovered."""
    # Create a task that started 5 minutes ago (still within 15 min timeout)
    recent_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.RUNNING.value,
        priority=PRIORITY_NORMAL,
        started_at=datetime.utcnow() - timedelta(minutes=5),
        attempt_count=1
    )
    db.add(recent_task)
    await db.commit()
    
    # Run recovery with 15 minute timeout
    recovered_count = await recover_stuck_tasks(db, timeout_minutes=15, max_attempts=3)
    
    assert recovered_count == 0
    
    # Task should still be RUNNING
    await db.refresh(recent_task)
    assert recent_task.state == TaskState.RUNNING.value


@pytest.mark.asyncio
async def test_recover_stuck_tasks_ignores_non_running_states(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that only RUNNING tasks are checked for recovery."""
    # Create old tasks in various states (all older than timeout)
    old_time = datetime.utcnow() - timedelta(minutes=20)
    
    task_queued = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_queued",
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        queued_at=old_time,
        attempt_count=1
    )
    task_needs_auth = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_auth",
        state=TaskState.NEEDS_AUTH.value,
        priority=PRIORITY_NORMAL,
        queued_at=old_time,
        attempt_count=1
    )
    task_failed = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id) + "_failed",
        state=TaskState.FAILED.value,
        priority=PRIORITY_NORMAL,
        queued_at=old_time,
        attempt_count=1
    )
    
    db.add_all([task_queued, task_needs_auth, task_failed])
    await db.commit()
    
    # Run recovery - should find 0 stuck tasks
    recovered_count = await recover_stuck_tasks(db, timeout_minutes=15, max_attempts=3)
    
    assert recovered_count == 0


@pytest.mark.asyncio
async def test_recover_multiple_stuck_tasks(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that multiple stuck tasks are all recovered."""
    old_time = datetime.utcnow() - timedelta(minutes=20)
    
    # Create 3 stuck tasks
    stuck_tasks = [
        ApplicationTask(
            run_id=str(application_run.id),
            job_id=str(job_posting.id) + f"_{i}",
            state=TaskState.RUNNING.value,
            priority=PRIORITY_NORMAL,
            started_at=old_time,
            attempt_count=1
        )
        for i in range(3)
    ]
    
    db.add_all(stuck_tasks)
    await db.commit()
    
    # Run recovery
    recovered_count = await recover_stuck_tasks(db, timeout_minutes=15, max_attempts=3)
    
    assert recovered_count == 3
    
    # All should be QUEUED
    for task in stuck_tasks:
        await db.refresh(task)
        assert task.state == TaskState.QUEUED.value


# ============================================================
# RESUME TASK TESTS
# ============================================================

@pytest.mark.asyncio
async def test_auto_retry_first_failure_goes_to_queued(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that first RUNNING → FAILED transition auto-retries to QUEUED."""
    from app.services.state_machine import transition_task
    
    # Create a RUNNING task with attempt_count=1 (first attempt)
    running_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.RUNNING.value,
        priority=PRIORITY_NORMAL,
        started_at=datetime.utcnow(),
        attempt_count=1
    )
    db.add(running_task)
    await db.commit()
    await db.refresh(running_task)
    
    # Transition to FAILED (first failure)
    task = await transition_task(
        db,
        str(running_task.id),
        TaskState.RUNNING,
        TaskState.FAILED,
        metadata={"error_code": "TEST_ERROR", "error_message": "Test failure"}
    )
    
    # Should auto-retry to QUEUED instead of staying in FAILED
    assert task.state == TaskState.QUEUED.value
    assert task.priority == 100  # Boosted priority for retry
    assert task.attempt_count == 1  # Stays at 1


@pytest.mark.asyncio
async def test_auto_retry_second_failure_stays_failed(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that second RUNNING → FAILED transition is terminal."""
    from app.services.state_machine import transition_task
    
    # Create a RUNNING task with attempt_count=2 (second attempt)
    running_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.RUNNING.value,
        priority=PRIORITY_NORMAL,
        started_at=datetime.utcnow(),
        attempt_count=2
    )
    db.add(running_task)
    await db.commit()
    await db.refresh(running_task)
    
    # Transition to FAILED (second failure)
    task = await transition_task(
        db,
        str(running_task.id),
        TaskState.RUNNING,
        TaskState.FAILED,
        metadata={"error_code": "TEST_ERROR", "error_message": "Test failure"}
    )
    
    # Should stay in FAILED (terminal state)
    assert task.state == TaskState.FAILED.value
    assert task.attempt_count == 2
    assert task.last_error_code == "TEST_ERROR"


@pytest.mark.asyncio
async def test_queued_to_running_increments_attempt_count(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that transitioning QUEUED → RUNNING increments attempt_count."""
    from app.services.state_machine import transition_task
    
    # Create a QUEUED task
    queued_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.QUEUED.value,
        priority=PRIORITY_NORMAL,
        attempt_count=0
    )
    db.add(queued_task)
    await db.commit()
    await db.refresh(queued_task)
    
    # Transition to RUNNING
    task = await transition_task(db, str(queued_task.id), None, TaskState.RUNNING)
    
    # attempt_count should increment
    assert task.state == TaskState.RUNNING.value
    assert task.attempt_count == 1
    assert task.started_at is not None


# ============================================================

@pytest.mark.asyncio
async def test_resume_failed_task_succeeds(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that a FAILED task can be manually resumed (safety valve)."""
    # Create a FAILED task
    failed_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.FAILED.value,
        priority=PRIORITY_NORMAL,
        attempt_count=2
    )
    db.add(failed_task)
    await db.commit()
    await db.refresh(failed_task)
    
    # Manual resume should succeed (FAILED → QUEUED allowed for manual recovery)
    resumed_task = await resume_task(db, str(failed_task.id))
    
    assert resumed_task.state == TaskState.QUEUED.value
    assert resumed_task.priority == PRIORITY_RESUMED  # Priority boost


@pytest.mark.asyncio
async def test_resume_needs_auth_task_to_queued(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that a NEEDS_AUTH task can be resumed to QUEUED."""
    # Create a NEEDS_AUTH task
    auth_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.NEEDS_AUTH.value,
        priority=PRIORITY_NORMAL,
        attempt_count=0
    )
    db.add(auth_task)
    await db.commit()
    await db.refresh(auth_task)
    
    # Resume the task
    resumed_task = await resume_task(db, str(auth_task.id))
    
    assert resumed_task.state == TaskState.QUEUED.value
    assert resumed_task.priority == PRIORITY_RESUMED


@pytest.mark.asyncio
async def test_resume_needs_user_task_to_queued(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that a NEEDS_USER task can be resumed to QUEUED."""
    # Create a NEEDS_USER task
    user_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.NEEDS_USER.value,
        priority=PRIORITY_NORMAL,
        attempt_count=0
    )
    db.add(user_task)
    await db.commit()
    await db.refresh(user_task)
    
    # Resume the task
    resumed_task = await resume_task(db, str(user_task.id))
    
    assert resumed_task.state == TaskState.QUEUED.value
    assert resumed_task.priority == PRIORITY_RESUMED


@pytest.mark.asyncio
async def test_resume_task_updates_queued_at_timestamp(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that resuming a task updates the queued_at timestamp."""
    old_time = datetime.utcnow() - timedelta(hours=1)
    
    # Create a NEEDS_USER task with old timestamp
    user_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.NEEDS_USER.value,
        priority=PRIORITY_NORMAL,
        queued_at=old_time,
        attempt_count=0
    )
    db.add(user_task)
    await db.commit()
    await db.refresh(user_task)
    
    # Resume the task
    resumed_task = await resume_task(db, str(user_task.id))
    
    # queued_at should be updated to recent time
    assert resumed_task.queued_at > old_time
    assert (datetime.utcnow() - resumed_task.queued_at).total_seconds() < 5  # Within 5 seconds


@pytest.mark.asyncio
async def test_resume_nonexistent_task_raises_error(db: AsyncSession):
    """Test that resuming a non-existent task raises ValueError."""
    with pytest.raises(ValueError, match="Task .* not found"):
        await resume_task(db, "00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_resume_task_gets_priority_boost(
    db: AsyncSession,
    application_run: ApplicationRun,
    job_posting: JobPosting
):
    """Test that manually resumed tasks get PRIORITY_RESUMED (100)."""
    # Create a NEEDS_AUTH task with normal priority
    auth_task = ApplicationTask(
        run_id=str(application_run.id),
        job_id=str(job_posting.id),
        state=TaskState.NEEDS_AUTH.value,
        priority=PRIORITY_NORMAL,
        attempt_count=0
    )
    db.add(auth_task)
    await db.commit()
    await db.refresh(auth_task)
    
    # Resume the task
    resumed_task = await resume_task(db, str(auth_task.id))
    
    assert resumed_task.priority == PRIORITY_RESUMED
