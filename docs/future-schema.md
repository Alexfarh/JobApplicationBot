# Future Schema (Phase 2+)

This document tracks database tables that will be added in future phases.

## Phase 2: Browser Automation

### remote_browser_sessions

Tracks browser sessions accessible via noVNC.

```sql
CREATE TABLE remote_browser_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES application_runs(id) NOT NULL,
    status VARCHAR NOT NULL,  -- active | expired | terminated
    provider VARCHAR NOT NULL DEFAULT 'novnc',
    user_console_url VARCHAR,  -- Signed URL for user access
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_heartbeat_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

**Why Phase 2:**
- Only needed when browser automation is implemented
- Requires noVNC infrastructure setup
- Must handle session lifecycle management

---

## Phase 3: Form Capture

### form_captures

Stores captured form questions and answers for approval requests.

```sql
CREATE TABLE form_captures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES application_tasks(id) NOT NULL UNIQUE,
    captured_at TIMESTAMP NOT NULL DEFAULT NOW(),
    fields JSONB NOT NULL  -- Array of {question, type, options, answer, source, confidence}
);
```

**Example `fields` JSONB:**
```json
[
  {
    "question": "Do you have experience with Python?",
    "type": "yes_no",
    "options": ["Yes", "No"],
    "answer": "Yes",
    "source": "resume_check",
    "confidence": "high"
  },
  {
    "question": "Years of experience with React?",
    "type": "number",
    "answer": "3",
    "source": "resume_analysis",
    "confidence": "medium"
  }
]
```

**Why Phase 3:**
- Only useful when auto-fill logic exists
- Requires integration with Greenhouse/Workday form scraping
- Needs approval UI to display captured forms

---

## Migration Strategy

When adding these tables:

1. Create new Alembic migration
2. Add models to `app/models/`
3. Update `app/models/__init__.py`
4. No changes needed to existing tables (clean separation)

## Scalability Notes

- All tables use UUIDs for primary keys (distributed-friendly)
- JSONB columns allow schema flexibility without migrations
- Indexes will be added based on actual query patterns in production
