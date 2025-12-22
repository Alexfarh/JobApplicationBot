# Approval Workflow (Event-Driven)

## Problem
When user approves an application, we need to submit it IMMEDIATELY even if the bot is currently processing another job. Session may expire if we wait too long.

## Solution: Event-Driven Interruption

### Flow

**Normal Operation:**
```
Worker: Dequeue Task A → Process → Submit
Worker: Dequeue Task B → Process → Submit
```

**When User Approves:**
```
1. User clicks "Approve" in dashboard
2. API marks task as APPROVED
3. API signals worker: approval_event.set()
4. Worker IMMEDIATELY:
   - Pauses current task (RUNNING → QUEUED with resume metadata)
   - Processes APPROVED task
   - Checks for other approvals
   - Resumes paused task
5. Continues normal operation
```

### State Transitions

```
PENDING_APPROVAL → APPROVED (when user approves)
APPROVED → RUNNING (worker interrupts to process)
APPROVED → EXPIRED (if session invalid)

RUNNING → QUEUED (pause current work when approval happens)
```

### Implementation

**Phase 1/2: asyncio.Event (in-process)**
```python
# Shared event flag
approval_event = asyncio.Event()

# API endpoint
@app.post("/approvals/{token}/approve")
async def approve(token):
    # Mark as approved
    approval.status = 'approved'
    task.state = 'APPROVED'
    
    # Signal worker
    approval_event.set()
    
    return {"message": "Submitting now..."}

# Worker
async def worker_loop():
    while True:
        if approval_event.is_set():
            await handle_approvals()
            approval_event.clear()
        
        task = await dequeue_next_task()
        if task:
            await process_task(task)
```

**Future: PostgreSQL LISTEN/NOTIFY**
When API and worker run as separate processes, use:
```python
# API
await db.execute("NOTIFY approval_channel, :task_id")

# Worker
connection.add_listener('approval_channel', on_approval)
```

### Duplicate Detection Integration

Before creating tasks for a run:
```python
# In POST /runs/{run_id}/jobs
for job_url in job_urls:
    job = get_or_create_job(job_url)
    
    # Check if already applied
    if job.has_been_applied_to:
        warnings.append(f"Skipped {job.company_name} - already applied on {job.last_applied_at}")
        continue
    
    # Create task
    task = ApplicationTask(run_id=run_id, job_id=job.id)
    db.add(task)
```

When task reaches SUBMITTED:
```python
# In worker
job.has_been_applied_to = True
job.last_applied_at = datetime.utcnow()
await db.commit()
```

## Benefits

✅ No polling - instant response to approvals  
✅ Prevents session expiry  
✅ Duplicate detection prevents applying twice  
✅ Clean state machine  
✅ Simple for Phase 1/2 (asyncio), scalable for later (PostgreSQL NOTIFY)
