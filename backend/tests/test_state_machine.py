"""
Tests for the state machine service.

Validates:
- All valid state transitions
- Invalid transitions raise InvalidTransitionError
- Priority boosting logic
- Auto-retry on first failure
- Job marking only on SUBMITTED
- REJECTED is terminal (user explicitly declined)
- Metadata persistence
"""
import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy import select

from app.models.application_task import ApplicationTask, TaskState
from app.models.job_posting import JobPosting
from app.models.application_run import ApplicationRun
from app.services.state_machine import (
    transition_task,
    can_transition,
    InvalidTransitionError,
)


@pytest_asyncio.fixture
async def job_posting(db):
    """Create a test job posting"""
    job = JobPosting(
        job_url="https://example.com/job/1",
        apply_url="https://example.com/job/1/apply",
        company_name="Test Corp",
        job_title="Software Engineer",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@pytest_asyncio.fixture
async def application_run(db, test_user):
    """Create a test application run"""
    run = ApplicationRun(
        user_id=test_user.id,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@pytest_asyncio.fixture
async def task(db, application_run, job_posting):
    """Create a test application task in QUEUED state"""
    task = ApplicationTask(
        run_id=application_run.id,
        job_id=job_posting.id,
        state=TaskState.QUEUED.value,
        priority=50,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# =============================================================================
# Valid Transitions
# =============================================================================

@pytest.mark.asyncio
async def test_queued_to_running(db, task):
    """Test QUEUED → RUNNING transition"""
    result = await transition_task(
        db,
        str(task.id),
        None,
        TaskState.RUNNING,
    )
    
    assert result.state == TaskState.RUNNING.value
    assert result.attempt_count == 1
    assert result.started_at is not None


@pytest.mark.asyncio
async def test_running_to_needs_auth(db, task):
    """Test RUNNING → NEEDS_AUTH transition"""
    # First move to RUNNING
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    # Then to NEEDS_AUTH
    result = await transition_task(db, str(task.id), None, TaskState.NEEDS_AUTH)
    
    assert result.state == TaskState.NEEDS_AUTH.value


@pytest.mark.asyncio
async def test_running_to_needs_user(db, task):
    """Test RUNNING → NEEDS_USER transition"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    result = await transition_task(db, str(task.id), None, TaskState.NEEDS_USER)
    
    assert result.state == TaskState.NEEDS_USER.value


@pytest.mark.asyncio
async def test_running_to_pending_approval(db, task):
    """Test RUNNING → PENDING_APPROVAL transition"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    result = await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    
    assert result.state == TaskState.PENDING_APPROVAL.value


@pytest.mark.asyncio
async def test_running_to_submitted(db, task, job_posting):
    """Test RUNNING → SUBMITTED transition and job marking"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    # Verify job not marked yet
    await db.refresh(job_posting)
    assert job_posting.has_been_applied_to is False
    
    # Transition to SUBMITTED
    result = await transition_task(db, str(task.id), None, TaskState.SUBMITTED)
    
    assert result.state == TaskState.SUBMITTED.value
    
    # Verify job is now marked as applied
    await db.refresh(job_posting)
    assert job_posting.has_been_applied_to is True
    assert job_posting.last_applied_at is not None


@pytest.mark.asyncio
async def test_pending_approval_to_approved(db, task):
    """Test PENDING_APPROVAL → APPROVED transition"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    result = await transition_task(db, str(task.id), None, TaskState.APPROVED)
    
    assert result.state == TaskState.APPROVED.value


@pytest.mark.asyncio
async def test_pending_approval_to_expired(db, task):
    """Test PENDING_APPROVAL → EXPIRED transition"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    result = await transition_task(db, str(task.id), None, TaskState.EXPIRED)
    
    assert result.state == TaskState.EXPIRED.value


@pytest.mark.asyncio
async def test_approved_to_running(db, task):
    """Test APPROVED → RUNNING transition"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    await transition_task(db, str(task.id), None, TaskState.APPROVED)
    result = await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    assert result.state == TaskState.RUNNING.value
    assert result.attempt_count == 2  # Should increment


# =============================================================================
# Priority Boosting
# =============================================================================

@pytest.mark.asyncio
async def test_needs_auth_to_queued(db, task):
    """Test NEEDS_AUTH → QUEUED transition (priority boost happens in Tasks API)"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.NEEDS_AUTH)
    
    result = await transition_task(db, str(task.id), None, TaskState.QUEUED)
    
    assert result.state == TaskState.QUEUED.value
    # Priority boost is handled by Tasks API resume endpoint, not state machine


@pytest.mark.asyncio
async def test_needs_user_to_queued(db, task):
    """Test NEEDS_USER → QUEUED transition (priority boost happens in Tasks API)"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.NEEDS_USER)
    
    result = await transition_task(db, str(task.id), None, TaskState.QUEUED)
    
    assert result.state == TaskState.QUEUED.value
    # Priority boost is handled by Tasks API resume endpoint, not state machine


# =============================================================================
# Auto-Retry Logic
# =============================================================================

@pytest.mark.asyncio
async def test_first_failure_auto_retry(db, task):
    """Test first failure auto-retries with boosted priority"""
    # First attempt
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    # First failure should auto-retry
    result = await transition_task(
        db,
        str(task.id),
        None,
        TaskState.FAILED,
        metadata={"error_code": "TIMEOUT", "error_message": "Connection timeout"}
    )
    
    # Should be back in QUEUED, not FAILED
    assert result.state == TaskState.QUEUED.value
    assert result.priority == 100  # Boosted for immediate retry
    assert result.attempt_count == 1
    assert result.last_error_code == "TIMEOUT"
    assert result.last_error_message == "Connection timeout"


@pytest.mark.asyncio
async def test_second_failure_terminal(db, task):
    """Test second failure becomes terminal FAILED state"""
    # First attempt and failure (auto-retry)
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.FAILED)
    
    # Second attempt
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    # Second failure should be terminal
    result = await transition_task(
        db,
        str(task.id),
        None,
        TaskState.FAILED,
        metadata={"error_code": "DOM_ERROR", "error_message": "Element not found"}
    )
    
    assert result.state == TaskState.FAILED.value  # Terminal state
    assert result.attempt_count == 2
    assert result.last_error_code == "DOM_ERROR"


# =============================================================================
# Invalid Transitions
# =============================================================================

@pytest.mark.asyncio
async def test_queued_to_submitted_invalid(db, task):
    """Test QUEUED → SUBMITTED is not allowed"""
    with pytest.raises(InvalidTransitionError):
        await transition_task(db, str(task.id), None, TaskState.SUBMITTED)


@pytest.mark.asyncio
async def test_submitted_is_terminal(db, task):
    """Test SUBMITTED cannot transition to anything"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.SUBMITTED)
    
    with pytest.raises(InvalidTransitionError):
        await transition_task(db, str(task.id), None, TaskState.QUEUED)


@pytest.mark.asyncio
async def test_failed_can_be_manually_resumed(db, task):
    """Test FAILED can be manually resumed via FAILED → QUEUED"""
    # Reach terminal FAILED state
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.FAILED)  # Auto-retry
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.FAILED)  # Now in FAILED
    
    # Manual resume allowed (for safety valve)
    result = await transition_task(db, str(task.id), None, TaskState.QUEUED)
    assert result.state == TaskState.QUEUED.value


@pytest.mark.asyncio
async def test_expired_can_be_manually_resumed(db, task):
    """Test EXPIRED can be manually resumed via EXPIRED → QUEUED"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    await transition_task(db, str(task.id), None, TaskState.EXPIRED)
    
    # Manual resume allowed (for approval TTL recovery)
    result = await transition_task(db, str(task.id), None, TaskState.QUEUED)
    assert result.state == TaskState.QUEUED.value


@pytest.mark.asyncio
async def test_pending_approval_to_rejected(db, task):
    """Test PENDING_APPROVAL → REJECTED when user declines submission"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    
    # User rejects the application
    result = await transition_task(
        db,
        str(task.id),
        None,
        TaskState.REJECTED,
        metadata={"rejection_notes": "Job requirements don't match experience"}
    )
    
    assert result.state == TaskState.REJECTED.value


@pytest.mark.asyncio
async def test_rejected_is_terminal(db, task):
    """Test REJECTED is a terminal state (cannot transition anywhere)"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    await transition_task(db, str(task.id), None, TaskState.REJECTED)
    
    # Attempt to transition from REJECTED should fail
    with pytest.raises(InvalidTransitionError):
        await transition_task(db, str(task.id), None, TaskState.QUEUED)


@pytest.mark.asyncio
async def test_needs_auth_to_running_invalid(db, task):
    """Test NEEDS_AUTH → RUNNING is not allowed (must go through QUEUED)"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.NEEDS_AUTH)
    
    with pytest.raises(InvalidTransitionError):
        await transition_task(db, str(task.id), None, TaskState.RUNNING)


# =============================================================================
# Metadata Persistence
# =============================================================================

@pytest.mark.asyncio
async def test_metadata_persistence(db, task):
    """Test error metadata is persisted correctly"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    result = await transition_task(
        db,
        str(task.id),
        None,
        TaskState.FAILED,
        metadata={
            "error_code": "AUTH_REQUIRED",
            "error_message": "Login page detected"
        }
    )
    
    # Auto-retry puts it back to QUEUED, but metadata should persist
    assert result.last_error_code == "AUTH_REQUIRED"
    assert result.last_error_message == "Login page detected"


# =============================================================================
# Job Posting Marking
# =============================================================================

@pytest.mark.asyncio
async def test_expired_does_not_mark_job(db, task, job_posting):
    """Test EXPIRED tasks don't mark job as applied (allows reapplication)"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.PENDING_APPROVAL)
    await transition_task(db, str(task.id), None, TaskState.EXPIRED)
    
    # Job should NOT be marked as applied
    await db.refresh(job_posting)
    assert job_posting.has_been_applied_to is False
    assert job_posting.last_applied_at is None


@pytest.mark.asyncio
async def test_failed_does_not_mark_job(db, task, job_posting):
    """Test FAILED tasks don't mark job as applied"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.FAILED)
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    await transition_task(db, str(task.id), None, TaskState.FAILED)  # Terminal
    
    # Job should NOT be marked as applied
    await db.refresh(job_posting)
    assert job_posting.has_been_applied_to is False


# =============================================================================
# Helper Function Tests
# =============================================================================

@pytest.mark.asyncio
async def test_can_transition_valid():
    """Test can_transition returns True for valid transitions"""
    assert await can_transition(TaskState.QUEUED, TaskState.RUNNING) is True
    assert await can_transition(TaskState.RUNNING, TaskState.NEEDS_AUTH) is True
    assert await can_transition(TaskState.NEEDS_AUTH, TaskState.QUEUED) is True


@pytest.mark.asyncio
async def test_can_transition_invalid():
    """Test can_transition returns False for invalid transitions"""
    assert await can_transition(TaskState.QUEUED, TaskState.SUBMITTED) is False
    assert await can_transition(TaskState.SUBMITTED, TaskState.QUEUED) is False
    assert await can_transition(TaskState.EXPIRED, TaskState.RUNNING) is False


@pytest.mark.asyncio
async def test_task_not_found(db):
    """Test transition with non-existent task ID"""
    with pytest.raises(ValueError, match="Task .* not found"):
        await transition_task(
            db,
            "00000000-0000-0000-0000-000000000000",
            None,
            TaskState.RUNNING
        )


# =============================================================================
# Stuck Task Recovery Transition
# =============================================================================

@pytest.mark.asyncio
async def test_running_to_queued_stuck_recovery(db, task):
    """Test RUNNING → QUEUED for stuck task recovery"""
    await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    # Simulate stuck task recovery
    result = await transition_task(db, str(task.id), None, TaskState.QUEUED)
    
    assert result.state == TaskState.QUEUED.value


# =============================================================================
# Optimistic Locking Tests
# =============================================================================

@pytest.mark.asyncio
async def test_from_state_none_skips_validation(db, task):
    """Test that from_state=None skips optimistic locking validation"""
    # Task starts in QUEUED
    assert task.state == TaskState.QUEUED.value
    
    # Transition with from_state=None should work even if we're "wrong" about current state
    result = await transition_task(db, str(task.id), None, TaskState.RUNNING)
    
    assert result.state == TaskState.RUNNING.value
    assert result.attempt_count == 1


@pytest.mark.asyncio
async def test_from_state_mismatch_raises_error(db, task):
    """Test that from_state mismatch raises ValueError"""
    # Task is in QUEUED
    assert task.state == TaskState.QUEUED.value
    
    # Try to transition from RUNNING (wrong state)
    with pytest.raises(ValueError, match="is in state QUEUED, expected RUNNING"):
        await transition_task(
            db,
            str(task.id),
            TaskState.RUNNING,  # Wrong from_state
            TaskState.NEEDS_AUTH
        )


@pytest.mark.asyncio
async def test_from_state_correct_allows_transition(db, task):
    """Test that correct from_state allows transition (optimistic locking success)"""
    # Task is in QUEUED
    assert task.state == TaskState.QUEUED.value
    
    # Transition with correct from_state
    result = await transition_task(
        db,
        str(task.id),
        TaskState.QUEUED,  # Correct from_state
        TaskState.RUNNING
    )
    
    assert result.state == TaskState.RUNNING.value
    assert result.attempt_count == 1
