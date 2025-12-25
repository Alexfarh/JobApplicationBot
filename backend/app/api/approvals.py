"""
Approvals API endpoints.
Handles approval requests for application submissions.
"""
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.approval_request import ApprovalRequest
from app.models.application_task import ApplicationTask, TaskState
from app.models.user import User
from app.api.auth import get_current_user
from app.services.state_machine import transition_task
from app.schemas.approval import (
    FormField,
    ApprovalRequestCreate,
    ApprovalResponse,
    ApprovalAction
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Default approval TTL (20 minutes)
APPROVAL_TTL_MINUTES = 20


# Endpoints
@router.post("/", response_model=ApprovalResponse, status_code=201)
async def create_approval_request(
    request: ApprovalRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an approval request for a task.
    
    The task must be in PENDING_APPROVAL state. Creates an approval request
    with a TTL (default 20 minutes). If not approved within TTL, task will
    be marked as EXPIRED.
    
    Returns the approval request with an expiration time.
    """
    # Verify task exists and belongs to user
    result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.id == str(request.task_id))
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found")
    
    if task.state != TaskState.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=409,
            detail=f"Task must be in PENDING_APPROVAL state, currently in {task.state}"
        )
    
    # Check if approval request already exists for this task
    existing = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.task_id == str(request.task_id),
            ApprovalRequest.status == "pending"
        )
    )
    existing_approval = existing.scalar_one_or_none()
    
    if existing_approval:
        # Return existing pending approval instead of creating duplicate
        logger.info(f"Returning existing approval request {existing_approval.id} for task {request.task_id}")
        return existing_approval
    
    # Create approval request
    expires_at = datetime.utcnow() + timedelta(minutes=request.ttl_minutes)
    
    approval = ApprovalRequest(
        task_id=str(request.task_id),
        user_id=str(current_user.id),
        form_data=[field.model_dump() for field in request.form_data],
        preview_url=request.preview_url,
        status="pending",
        expires_at=expires_at
    )
    
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    logger.info(f"Created approval request {approval.id} for task {request.task_id}, expires at {expires_at}")
    
    return approval


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval_request(
    approval_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an approval request by ID.
    
    Only the owner can access their approval requests.
    """
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == str(approval_id))
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval request {approval_id} not found")
    
    # Verify ownership (both are UUID objects from GUID columns)
    if str(approval.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail=f"Approval request {approval_id} not found")
    
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_or_reject(
    approval_id: UUID,
    action: ApprovalAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve or reject an approval request.
    
    If approved:
    - Marks approval as 'approved'
    - Transitions task to APPROVED state
    - Task will be picked up by worker for submission
    
    If rejected:
    - Marks approval as 'rejected'
    - Transitions task to REJECTED state (terminal, user explicitly declined to submit)
    
    Returns 409 if approval has expired or is already processed.
    """
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == str(approval_id))
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval request {approval_id} not found")
    
    # Verify ownership (both are UUID objects from GUID columns)
    if str(approval.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail=f"Approval request {approval_id} not found")
    
    # Check if already processed
    if approval.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval request already {approval.status}"
        )
    
    # Check if expired
    if datetime.utcnow() > approval.expires_at:
        # Mark as expired
        approval.status = "expired"
        await db.commit()
        
        # Transition task to EXPIRED
        await transition_task(
            db=db,
            task_id=approval.task_id,
            from_state=TaskState.PENDING_APPROVAL,
            to_state=TaskState.EXPIRED
        )
        
        raise HTTPException(
            status_code=409,
            detail=f"Approval request expired at {approval.expires_at}"
        )
    
    # Process approval/rejection
    if action.approved:
        approval.status = "approved"
        approval.approved_at = datetime.utcnow()
        
        # Transition task to APPROVED state
        await transition_task(
            db=db,
            task_id=approval.task_id,
            from_state=TaskState.PENDING_APPROVAL,
            to_state=TaskState.APPROVED
        )
        
        logger.info(f"Approval {approval_id} approved by user {current_user.id}, task {approval.task_id} → APPROVED")
    else:
        # User rejected the application - move to REJECTED
        approval.status = "rejected"
        
        # Transition task to REJECTED (user explicitly rejected submission)
        await transition_task(
            db=db,
            task_id=approval.task_id,
            from_state=TaskState.PENDING_APPROVAL,
            to_state=TaskState.REJECTED,
            metadata={"rejection_notes": action.notes} if action.notes else None
        )
        
        logger.info(f"Approval {approval_id} rejected by user {current_user.id}, task {approval.task_id} → REJECTED")
    
    await db.commit()
    await db.refresh(approval)
    
    return approval
