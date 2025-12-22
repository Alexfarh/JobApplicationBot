# JobApplicationBot Backend

FastAPI-based backend for job application automation system.

## Phase 1 Progress

### ✅ Completed
- [x] Project structure created
- [x] Database models defined (5 tables)
  - users
  - application_runs
  - job_postings
  - application_tasks (with state enum & queue indexes)
  - approval_requests
- [x] State machine service with transition validation
- [x] Queue service with dequeue logic (SELECT FOR UPDATE SKIP LOCKED)
- [x] Stuck-task recovery service
- [x] Priority system (50 default, 100 for resumed tasks)
- [x] Alembic configuration

### 🚧 In Progress
- [ ] Alembic initial migration
- [ ] FastAPI app initialization
- [ ] API endpoints (auth, runs, jobs, tasks, approvals)
- [ ] Frontend Next.js dashboard

### ⏳ TODO
- [ ] Tests (pytest)
- [ ] Documentation

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run migrations (once created):
```bash
alembic upgrade head
```

5. Start the server (once main.py created):
```bash
uvicorn app.main:app --reload
```

## Database Models

### State Machine
All state transitions go through `app.services.state_machine.transition_task()`.

**Allowed states:**
- `QUEUED` → `RUNNING`
- `RUNNING` → `NEEDS_AUTH | NEEDS_USER | PENDING_APPROVAL | SUBMITTED | FAILED | EXPIRED`
- `NEEDS_AUTH` → `QUEUED` (after user auth)
- `NEEDS_USER` → `QUEUED` (after user input)
- `PENDING_APPROVAL` → `APPROVED | EXPIRED`
- `APPROVED` → `RUNNING`
- `FAILED` → `QUEUED` (manual resume)

### Queue Logic
Dequeue order: `priority DESC, queued_at ASC`

Priority levels:
- 100 = Resumed/boosted tasks
- 50 = Default tasks

## Project Structure

```
backend/
├── alembic/           # Database migrations
│   ├── versions/      # Migration files
│   └── env.py         # Alembic config
├── app/
│   ├── models/        # SQLAlchemy models
│   ├── services/      # Business logic
│   │   ├── state_machine.py  # State transitions
│   │   └── queue.py           # Queue dequeue logic
│   ├── api/           # FastAPI routes (TODO)
│   ├── config.py      # Settings
│   └── database.py    # DB connection
├── tests/             # Pytest tests (TODO)
├── requirements.txt
└── .env.example
```
