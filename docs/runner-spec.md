# Runner Specification (V1)

## Queue processing
- One worker
- One active run
- Dequeue using:
  SELECT ... FOR UPDATE SKIP LOCKED

## Retry policy
- Transient failures: auto-retry once
- Second failure → FAILED
- NEEDS_AUTH is never auto-retried

## Resume behavior
- Resume sets state → QUEUED
- Priority boost sends task to front of queue

## Idempotency
Before submit:
- fingerprint = sha256(run_id + user_id + apply_url)
- If fingerprint already submitted → abort

## Stuck-task recovery
- RUNNING older than timeout → QUEUED
