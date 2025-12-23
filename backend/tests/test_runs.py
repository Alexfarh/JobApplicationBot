"""
Tests for runs endpoints (CRUD operations).

This test suite validates the ApplicationRun endpoints:
- CREATE: POST /api/runs (create new batch run)
- READ: GET /api/runs (list all user's runs)
- READ: GET /api/runs/{run_id} (get specific run with task counts)
- DELETE: DELETE /api/runs/{run_id} (delete run and cascade to tasks)

Security validation:
- User isolation (can't see/modify other users' runs)
- Ownership checks (404 vs 403 errors)

All fixtures (async_client, db, test_user) handle cleanup via try/finally blocks.
Each test gets a fresh in-memory SQLite database.
"""
import pytest
from uuid import uuid4, UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.application_run import ApplicationRun
from app.models.application_task import ApplicationTask, TaskState
from app.models.user import User


@pytest.mark.asyncio
async def test_create_run(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Create a new ApplicationRun
    
    What happens:
    1. POST /api/runs with name and description
    2. Creates ApplicationRun record in database
    3. Sets status to "created" (initial state)
    4. Links to user_id
    5. Initializes task counts to 0
    6. Returns 201 Created with run details
    
    Verifies:
    - API returns all fields (name, description, status, user_id)
    - Initial status is "running" (default)
    - Task counts start at 0
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request to create run
        response = await async_client.post(
            f"/api/runs?user_id={test_user.id}",
            json={
                "name": "Test Run",
                "description": "Testing run creation"
            }
        )
        
        # Verify API response
        assert response.status_code == 201, "Should return 201 Created"
        data = response.json()
        assert data["name"] == "Test Run"
        assert data["description"] == "Testing run creation"
        assert data["status"] == "running", "Default status should be 'running'"
        assert data["user_id"] == str(test_user.id)
        assert data["total_tasks"] == 0, "New run should have 0 tasks"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_list_runs_empty_no_users(async_client: AsyncClient, db: AsyncSession):
    """
    Test: List runs when NO USERS exist in database
    
    What happens:
    1. Database is completely empty (no users at all)
    2. GET /api/runs with random user_id
    3. Query finds no runs for this non-existent user
    4. Returns 200 with empty list
    
    Verifies:
    - Empty DB is handled gracefully
    - Returns total=0 and runs=[]
    - No errors when user doesn't exist
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request with random user_id (no users exist)
        fake_user_id = uuid4()
        response = await async_client.get(f"/api/runs?user_id={fake_user_id}")
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0, "Should have 0 runs"
        assert data["runs"] == [], "Should return empty list"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_list_runs_empty_single_user(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: List runs when user exists but has NO runs yet
    
    What happens:
    1. User exists in database (test_user fixture)
    2. GET /api/runs for this user
    3. Database query finds 0 runs for this user_id
    4. Returns 200 with empty list
    
    Verifies:
    - Empty result is handled gracefully for existing user
    - Returns total=0 and runs=[]
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request to list runs for existing user with no runs
        response = await async_client.get(f"/api/runs?user_id={test_user.id}")
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0, "Should have 0 runs"
        assert data["runs"] == [], "Should return empty list"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_list_runs_empty_multiple_users(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: List runs when multiple users exist, querying user with no runs
    
    What happens:
    1. test_user exists (no runs)
    2. other_user exists WITH runs
    3. GET /api/runs for test_user
    4. Query filters by user_id, finds 0 runs for test_user
    5. Returns empty list (doesn't return other_user's runs)
    
    Verifies:
    - User isolation when other users have data
    - Empty result for user with no runs
    - Doesn't leak other users' runs
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create other user with runs
        other_user = User(email="other@example.com")
        db.add(other_user)
        await db.flush()
        
        run1 = ApplicationRun(user_id=other_user.id, name="Other Run 1", status="created")
        run2 = ApplicationRun(user_id=other_user.id, name="Other Run 2", status="running")
        db.add_all([run1, run2])
        await db.commit()
        
        # Make API request as test_user (who has no runs)
        response = await async_client.get(f"/api/runs?user_id={test_user.id}")
        
        # Verify API response: empty for test_user
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0, "test_user should have 0 runs"
        assert data["runs"] == [], "Should not see other user's runs"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_list_runs_with_data(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: List runs when user HAS runs
    
    What happens:
    1. Create 2 runs in database for this user
    2. GET /api/runs queries database
    3. Returns runs sorted by created_at DESC (newest first)
    4. Each run includes basic fields (no task counts for list view)
    
    Verifies:
    - Returns correct count (total=2)
    - Returns all runs
    - Sorts by created_at DESC (Run 2 created after Run 1, so appears first)
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create multiple runs in database
        run1 = ApplicationRun(user_id=test_user.id, name="Run 1", status="created")
        run2 = ApplicationRun(user_id=test_user.id, name="Run 2", status="running")
        db.add_all([run1, run2])
        await db.commit()
        
        # Make API request to list runs
        response = await async_client.get(f"/api/runs?user_id={test_user.id}")
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2, "Should have 2 runs"
        # Sorted by created_at DESC (newest first)
        assert data["runs"][0]["name"] == "Run 2", "Newest run should be first"
        assert data["runs"][1]["name"] == "Run 1", "Older run should be second"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_list_runs_isolation(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: User ISOLATION - users only see their own runs
    
    What happens:
    1. Create run for test_user
    2. Create run for OTHER user (different user_id)
    3. GET /api/runs?user_id={test_user.id}
    4. Query filters by user_id (WHERE user_id = ?)
    5. Returns ONLY test_user's run, not other user's run
    
    Verifies:
    - User can only see their own runs (security)
    - Returns total=1 (not 2)
    - Returns only "My Run" (not "Other Run")
    
    Security: Critical for multi-tenant application. Users must not see
    other users' data.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create run for test user
        run1 = ApplicationRun(user_id=test_user.id, name="My Run", status="created")
        
        # Setup: Create run for DIFFERENT user
        other_user = User(email="other@example.com")
        db.add(other_user)
        await db.flush()
        run2 = ApplicationRun(user_id=other_user.id, name="Other Run", status="created")
        
        db.add_all([run1, run2])
        await db.commit()
        
        # Make API request as test_user
        response = await async_client.get(f"/api/runs?user_id={test_user.id}")
        
        # Verify API response: only test_user's run
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1, "Should only see own run, not other user's"
        assert data["runs"][0]["name"] == "My Run"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_get_run_success(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Get a SPECIFIC run (happy path)
    
    What happens:
    1. Create run in database
    2. GET /api/runs/{run_id}?user_id={user_id}
    3. Helper function validates:
       - Run exists (404 if not)
       - User owns run (403 if not)
    4. Returns run with task counts
    
    Verifies:
    - Returns 200 OK
    - Returns correct run ID and name
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create run
        run = ApplicationRun(user_id=test_user.id, name="Test Run", status="created")
        db.add(run)
        await db.commit()
        
        # Make API request to get specific run
        response = await async_client.get(f"/api/runs/{run.id}?user_id={test_user.id}")
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(run.id)
        assert data["name"] == "Test Run"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_get_run_not_found_empty_db(async_client: AsyncClient, test_user: User):
    """
    Test: Get run that DOESN'T EXIST (empty database, 404 error)
    
    What happens:
    1. Database has no runs at all
    2. GET /api/runs/{fake_uuid}?user_id={user_id}
    3. Helper function queries database: SELECT ... WHERE id = fake_uuid
    4. No row found → raises HTTPException(404)
    5. Returns 404 with "not found" message
    
    Verifies:
    - Non-existent run returns 404 when DB is empty
    - Error message mentions "not found"
    
    Security: Returns 404 (not 403) because run doesn't exist at all.
    This prevents information leakage (attacker can't enumerate valid IDs).
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request with non-existent run ID (DB has no runs)
        fake_id = uuid4()
        response = await async_client.get(f"/api/runs/{fake_id}?user_id={test_user.id}")
        
        # Verify 404 response
        assert response.status_code == 404, "Should return 404 for non-existent run"
        assert "not found" in response.json()["detail"].lower()
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_get_run_not_found_with_existing_runs(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Get run that DOESN'T EXIST (other runs exist, 404 error)
    
    What happens:
    1. Database has existing runs (for test_user)
    2. GET /api/runs/{fake_uuid} with ID that doesn't match any run
    3. Helper function queries: SELECT ... WHERE id = fake_uuid
    4. No row found (even though other runs exist) → HTTPException(404)
    5. Returns 404 with "not found" message
    
    Verifies:
    - Query correctly filters by run_id (not just checking if runs table is empty)
    - Returns 404 for non-existent ID even when other runs exist
    - Error message mentions "not found"
    
    This ensures the WHERE clause is working correctly.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create existing runs for test_user
        run1 = ApplicationRun(user_id=test_user.id, name="Existing Run 1", status="created")
        run2 = ApplicationRun(user_id=test_user.id, name="Existing Run 2", status="running")
        db.add_all([run1, run2])
        await db.commit()
        
        # Make API request with non-existent run ID (other runs exist)
        fake_id = uuid4()
        response = await async_client.get(f"/api/runs/{fake_id}?user_id={test_user.id}")
        
        # Verify 404 response
        assert response.status_code == 404, "Should return 404 for non-existent run"
        assert "not found" in response.json()["detail"].lower()
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_get_run_wrong_user(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Get run that exists but belongs to ANOTHER USER (403 error)
    
    What happens:
    1. Other user creates a run
    2. test_user tries to GET /api/runs/{other_user_run_id}
    3. Helper function finds run EXISTS (id is valid)
    4. BUT run.user_id != test_user.id → FORBIDDEN
    5. Returns 403 with "access denied" message
    
    Verifies:
    - Returns 403 (not 404) when run exists but user doesn't own it
    - Error message mentions "access denied"
    
    Security: Critical distinction between 404 and 403:
    - 404 = "run doesn't exist" (or you don't own it, to prevent enumeration)
    - 403 = "run exists, but you don't have permission"
    
    Our implementation: Log user IDs server-side but return generic "access denied".
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create run for OTHER user
        other_user = User(email="other@example.com")
        db.add(other_user)
        await db.flush()
        
        run = ApplicationRun(user_id=other_user.id, name="Other Run", status="created")
        db.add(run)
        await db.commit()
        
        # Make API request as test_user (wrong user)
        response = await async_client.get(f"/api/runs/{run.id}?user_id={test_user.id}")
        
        # Verify 403 response
        assert response.status_code == 403, "Should return 403 when accessing other user's run"
        assert "access denied" in response.json()["detail"].lower()
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_get_run_with_task_counts(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Get run WITH task counts (aggregated from tasks table)
    
    What happens:
    1. Create run with 5 tasks in different states:
       - 2 QUEUED
       - 1 RUNNING
       - 1 SUBMITTED
       - 1 FAILED
    2. GET /api/runs/{run_id} calls get_run_with_task_counts() helper
    3. Helper executes SQL query:
       SELECT state, COUNT(*) FROM application_tasks 
       WHERE run_id = ? GROUP BY state
    4. Returns counts as separate fields
    
    Verifies:
    - total_tasks = 5 (sum of all states)
    - queued_tasks = 2
    - running_tasks = 1
    - submitted_tasks = 1
    - failed_tasks = 1
    
    This is CRITICAL for dashboard display: user sees how many tasks are
    in each state without loading all task records.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create run
        run = ApplicationRun(user_id=test_user.id, name="Test Run", status="created")
        db.add(run)
        await db.flush()
        
        # Setup: Create tasks in different states
        task1 = ApplicationTask(run_id=run.id, job_id=1, state=TaskState.QUEUED)
        task2 = ApplicationTask(run_id=run.id, job_id=2, state=TaskState.QUEUED)
        task3 = ApplicationTask(run_id=run.id, job_id=3, state=TaskState.RUNNING)
        task4 = ApplicationTask(run_id=run.id, job_id=4, state=TaskState.SUBMITTED)
        task5 = ApplicationTask(run_id=run.id, job_id=5, state=TaskState.FAILED)
        
        db.add_all([task1, task2, task3, task4, task5])
        await db.commit()
        
        # Make API request to get run with counts
        response = await async_client.get(f"/api/runs/{run.id}?user_id={test_user.id}")
        
        # Verify API response includes accurate counts
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 5, "Should count all tasks"
        assert data["queued_tasks"] == 2, "Should count 2 queued tasks"
        assert data["running_tasks"] == 1, "Should count 1 running task"
        assert data["submitted_tasks"] == 1, "Should count 1 submitted task"
        assert data["failed_tasks"] == 1, "Should count 1 failed task"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_delete_run_success(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Delete a run (happy path)
    
    What happens:
    1. Create run in database
    2. DELETE /api/runs/{run_id}?user_id={user_id}
    3. Helper function validates ownership (404/403)
    4. Executes: DELETE FROM application_runs WHERE id = ?
    5. Returns 204 No Content (successful deletion)
    
    Verifies:
    - Returns 204 status code
    - Run is actually removed from database
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create run
        run = ApplicationRun(user_id=test_user.id, name="Test Run", status="created")
        db.add(run)
        await db.commit()
        run_id = run.id
        
        # Make API request to delete run
        response = await async_client.delete(f"/api/runs/{run_id}?user_id={test_user.id}")
        
        # Verify deletion response
        assert response.status_code == 204, "Should return 204 No Content"
        
        # Verify database state: run is gone
        result = await db.execute(
            select(ApplicationRun).where(ApplicationRun.id == run_id)
        )
        assert result.scalar_one_or_none() is None, "Run should be deleted from database"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_delete_run_cascade(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Delete run CASCADE deletes tasks (referential integrity)
    
    What happens:
    1. Create run with associated task
    2. DELETE /api/runs/{run_id}
    3. SQLAlchemy model has: relationship("ApplicationTask", cascade="all, delete-orphan")
    4. Database FK has: ON DELETE CASCADE
    5. Deleting run AUTOMATICALLY deletes all its tasks
    
    Verifies:
    - Run is deleted
    - Task is also deleted (not orphaned)
    
    This is CRITICAL for data integrity: we don't want orphaned tasks
    with run_id pointing to non-existent run.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create run with task
        run = ApplicationRun(user_id=test_user.id, name="Test Run", status="created")
        db.add(run)
        await db.flush()
        
        task = ApplicationTask(run_id=run.id, job_id=1, state=TaskState.QUEUED)
        db.add(task)
        await db.commit()
        
        task_id = task.id
        run_id = run.id
        
        # Make API request to delete run
        response = await async_client.delete(f"/api/runs/{run_id}?user_id={test_user.id}")
        assert response.status_code == 204
        
        # Verify database state: task was also deleted (cascade)
        result = await db.execute(
            select(ApplicationTask).where(ApplicationTask.id == task_id)
        )
        assert result.scalar_one_or_none() is None, "Task should be deleted via cascade"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_delete_run_not_found(async_client: AsyncClient, test_user: User):
    """
    Test: Delete run that DOESN'T EXIST (404 error)
    
    What happens:
    1. DELETE /api/runs/{fake_uuid}
    2. Helper function queries: SELECT ... WHERE id = fake_uuid
    3. No row found → raises HTTPException(404)
    4. Returns 404
    
    Verifies:
    - Cannot delete non-existent run
    - Returns 404 (not 500)
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Make API request to delete non-existent run
        fake_id = uuid4()
        response = await async_client.delete(f"/api/runs/{fake_id}?user_id={test_user.id}")
        
        # Verify 404 response
        assert response.status_code == 404, "Should return 404 for non-existent run"
        
    except Exception as e:
        raise e


@pytest.mark.asyncio
async def test_delete_run_wrong_user(async_client: AsyncClient, db: AsyncSession, test_user: User):
    """
    Test: Delete run belonging to ANOTHER USER (403 error)
    
    What happens:
    1. Other user creates run
    2. test_user tries DELETE /api/runs/{other_user_run_id}
    3. Helper function finds run EXISTS
    4. BUT run.user_id != test_user.id → FORBIDDEN
    5. Returns 403
    
    Verifies:
    - Cannot delete other users' runs (security)
    - Returns 403 (access denied)
    
    Security: CRITICAL. Prevents user from deleting others' data.
    
    Cleanup: Automatic via db fixture (try/finally)
    """
    try:
        # Setup: Create run for OTHER user
        other_user = User(email="other@example.com")
        db.add(other_user)
        await db.flush()
        
        run = ApplicationRun(user_id=other_user.id, name="Other Run", status="created")
        db.add(run)
        await db.commit()
        
        # Make API request as test_user (wrong user)
        response = await async_client.delete(f"/api/runs/{run.id}?user_id={test_user.id}")
        
        # Verify 403 response
        assert response.status_code == 403, "Should return 403 when deleting other user's run"
        
    except Exception as e:
        raise e
