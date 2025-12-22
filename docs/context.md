# JobApplicationBot — Master Context (V1)

## Goal
Automate job applications in small batches with minimal supervision:
- Fill application forms
- Upload resume
- Pause ONLY when user action is required
- Require approval before final submission when drafts are unavailable

This is a LOCAL, non-commercial system built for learning and personal use.

---

## Core Design Decisions (Locked)

- ONE active ApplicationRun at a time
- PostgreSQL is both source of truth AND queue
- Playwright drives a real browser
- Remote browser access via noVNC (Pattern A)
- Email notifications only
- Greenhouse is first-class ATS in V1
- Workday is partial support (auth pause/resume only)
- Approval TTL default = 20 minutes
- Resume / retry moves task to FRONT of queue
- Optimistic answers allowed, but NEVER lying

---

## Key Objects

- ApplicationRun — one batch
- ApplicationTask — one job application (queue unit)
- RemoteBrowserSession — persistent browser session
- FormCapture — questions + answers used
- ApprovalRequest — approval token + TTL

---

## Queues (Dashboard Views)

These are NOT separate tables — they are views over task state:
- Needs Auth → `NEEDS_AUTH`
- Needs User → `NEEDS_USER`
- Pending Approval → `PENDING_APPROVAL`
- Failed / Expired → `FAILED`, `EXPIRED`

---

## Workday Policy (Strict)

- NEVER auto-create accounts
- NEVER bypass OTP / CAPTCHA
- If login/setup appears:
  - Move ONLY that task to `NEEDS_AUTH`
  - Continue batch
- User completes login inside SAME remote session (noVNC)
- Resume continues from exact stopping point

---

## Optimistic Answer Policy

- Forced Yes/No:
  - Choose NO if no resume evidence exists
- Free-text explanation:
  - Honest optimistic phrasing allowed
  - “Actively learning, can ramp quickly”
- NEVER claim experience not in resume
- NEVER mention certifications unless asked

---

## Authority Order

When in doubt:
1. `.github/copilot-instructions.md`
2. `CONTEXT.md`
3. `/docs/*.md`
4. Ask for clarification — do NOT invent behavior
