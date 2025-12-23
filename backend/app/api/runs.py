"""
Application Run endpoints.

A run represents a batch of job applications to process.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.application_run import ApplicationRun
from app.models.application_task import ApplicationTask


router = APIRouter()


# Pydantic schemas
class CreateRunRequest(BaseModel):
    """Request to create a new application run."""
    name: str
    description: Optional[str] = None


class RunResponse(BaseModel):
    """Response with run details."""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Task counts
    total_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    submitted_tasks: int = 0
    failed_tasks: int = 0
    
    class Config:
        from_attributes = True  # Allows creating from SQLAlchemy models


class RunListResponse(BaseModel):
    """List of runs."""
    runs: List[RunResponse]
    total: int


# Endpoints
@router.post("/", response_model=RunResponse, status_code=201)
async def create_run(
    request: CreateRunRequest,
    user_id: str,  # TODO: Get from auth token in Phase 2
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new application run.
    
    A run is a batch of job applications to process.
    After creating, add jobs via POST /runs/{run_id}/jobs
    """
    try:
        run = ApplicationRun(
            user_id=UUID(user_id),
            name=request.name,
            description=request.description,
            status="created"
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
        )
    
    except Exception as e:
        await db.rollback()
        print(f"❌ Error creating run: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create run. Please try again."
        )


@router.get("/", response_model=RunListResponse)
async def list_runs(
    user_id: str,  # TODO: Get from auth token in Phase 2
    db: AsyncSession = Depends(get_db)
):
    """
    List all runs for a user, sorted by most recent first.
    """
    try:
        result = await db.execute(
            select(ApplicationRun)
            .where(ApplicationRun.user_id == UUID(user_id))
            .order_by(ApplicationRun.created_at.desc())
        )
        runs = result.scalars().all()
        
        # Get task counts for each run
        run_responses = []
        for run in runs:
            # Count tasks by state
            task_result = await db.execute(
                select(ApplicationTask)
                .where(ApplicationTask.run_id == run.id)
            )
            tasks = task_result.scalars().all()
            
            run_responses.append(RunResponse(
                id=str(run.id),
                user_id=str(run.user_id),
                name=run.name,
                description=run.description,
                status=run.status,
                created_at=run.created_at,
                started_at=run.started_at,
                completed_at=run.completed_at,
                total_tasks=len(tasks),
                queued_tasks=sum(1 for t in tasks if t.state == "QUEUED"),
                running_tasks=sum(1 for t in tasks if t.state == "RUNNING"),
                submitted_tasks=sum(1 for t in tasks if t.state == "SUBMITTED"),
                failed_tasks=sum(1 for t in tasks if t.state == "FAILED"),
            ))
        
        return RunListResponse(
            runs=run_responses,
            total=len(run_responses)
        )
    
    except Exception as e:
        print(f"❌ Error listing runs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch runs. Please try again."
        )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    user_id: str,  # TODO: Get from auth token in Phase 2
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific run.
    """
    try:
        result = await db.execute(
            select(ApplicationRun)
            .where(
                ApplicationRun.id == UUID(run_id),
                ApplicationRun.user_id == UUID(user_id)
            )
        )
        run = result.scalar_one_or_none()
        
        if not run:
            raise HTTPException(
                status_code=404,
                detail="Run not found."
            )
        
        # Count tasks
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
            total_tasks=len(tasks),
            queued_tasks=sum(1 for t in tasks if t.state == "QUEUED"),
            running_tasks=sum(1 for t in tasks if t.state == "RUNNING"),
            submitted_tasks=sum(1 for t in tasks if t.state == "SUBMITTED"),
            failed_tasks=sum(1 for t in tasks if t.state == "FAILED"),
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"❌ Error fetching run: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch run details. Please try again."
        )


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    user_id: str,  # TODO: Get from auth token in Phase 2
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a run and all its associated tasks.
    
    Note: Tasks will be deleted via CASCADE constraint.
    """
    try:
        result = await db.execute(
            select(ApplicationRun)
            .where(
                ApplicationRun.id == UUID(run_id),
                ApplicationRun.user_id == UUID(user_id)
            )
        )
        run = result.scalar_one_or_none()
        
        if not run:
            raise HTTPException(
                status_code=404,
                detail="Run not found."
            )
        
        await db.delete(run)
        await db.commit()
        
        return None  # 204 No Content
    
    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()
        print(f"❌ Error deleting run: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete run. Please try again."
        )
