# JobApplicationBot (Local V1)

A local, research-focused job application automation system that applies to job postings in small batches, pauses only when user action is required, and safely submits applications with human approval when needed.

> ⚠️ This project is for **personal use and learning only**.  
> It is not intended as a commercial service or to bypass platform safeguards.

---

## Overview

JobApplicationBot automates the repetitive parts of job applications while respecting real-world constraints imposed by Applicant Tracking Systems (ATS):

- Auth walls (e.g., Workday accounts)
- Session expiration
- Non-uniform application forms
- Lack of draft/save functionality
- Human judgment requirements

Instead of forcing users to babysit applications, the system:
- Processes jobs in small batches
- Pauses **per-job**, not globally
- Allows the user to intervene from their phone
- Requires approval before final submission when appropriate

---

## Key Features (V1)

- **Batch-based application runs**
  - One active run at a time
  - Each job is an independent queue task

- **PostgreSQL-backed task queue**
  - Uses `SELECT … FOR UPDATE SKIP LOCKED`
  - No Redis required in V1

- **Remote browser session (noVNC)**
  - User can complete logins, OTPs, and setup from their phone
  - Same browser session is shared with automation

- **Conditional approval model**
  - If no draft/save exists:
    - Bot fills to final review
    - Captures questions & answers
    - Waits for user approval before submit

- **Smart pause & resume**
  - Jobs requiring authentication move to `NEEDS_AUTH`
  - Jobs needing clarification move to `NEEDS_USER`
  - Other jobs continue automatically

- **Optimistic but honest answering**
  - Never lies about experience
  - Uses honest “actively learning / ramping quickly” language when appropriate

---

## System Architecture (High Level)

ApplicationRun (batch)
└─ ApplicationTask (queue unit)
├─ QUEUED
├─ RUNNING
├─ NEEDS_AUTH
├─ NEEDS_USER
├─ PENDING_APPROVAL
├─ APPROVED
├─ SUBMITTED / FAILED / EXPIRED


- One **runner**
- One **browser session**
- Many **tasks**, each isolated

---

## Supported Platforms

### V1
- **Greenhouse** (first-class support)

### Partial Support
- **Workday**
  - Auth pause/resume only
  - No account auto-creation
  - Iterative hardening

### Explicitly Out of Scope (V1)
- CAPTCHA bypass
- Auto account creation
- SMS notifications
- Multiple concurrent runs

---

## Approval & Safety Model

- Default approval TTL: **20 minutes**
- One-time approval tokens
- Session re-validation before submit
- Expired approvals → task marked `EXPIRED`
- Idempotency guard prevents duplicate submissions

---

## Data & Queue Design

- PostgreSQL is the **single source of truth**
- Tasks dequeued with row-level locking
- All state transitions enforced through a single transition function
- Artifacts (screenshots, HTML snippets) saved for debugging

---

## Security Notes

- Remote browser access is:
  - Authenticated
  - Token-gated
  - HTTPS-only
- No credentials stored for ATS platforms
- No password manager integration in V1

---

## Project Structure

/
backend/ # FastAPI + runner
dashboard/ # Web UI
docs/ # Architecture & specs
CONTEXT.md # Master design decisions
.github/
copilot-instructions.md


---

## Documentation

Design authority (in order):
1. `.github/copilot-instructions.md`
2. `CONTEXT.md`
3. `/docs/*.md`

Key docs:
- `docs/data-model.md`
- `docs/runner-spec.md`
- `docs/remote-session-novnc.md`
- `docs/risk-register.md`

---

## Development Status

- ✅ Architecture locked
- ✅ Risk analysis complete
- ⏳ Phase 1: DB + API + dashboard (in progress)
- ⏳ Phase 2: Runner skeleton + noVNC
- ⏳ Phase 3: Greenhouse automation

---

## Disclaimer

This project does **not** attempt to evade platform protections or violate terms of service.  
It automates user actions **only where permitted**, and requires human intervention where required.

---

## Why This Exists

This project exists to explore:
- Automate the process of mass job applications
- Distributed task orchestration without Redis
- Browser automation under real-world constraints
- Human-in-the-loop automation design
- Resilient queue & state machine design
