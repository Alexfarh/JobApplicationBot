# Risk Register (V1)

## Queue risks
- Double processing → SKIP LOCKED + unique constraints
- State drift → centralized transition function
- Infinite retries → retry allowlist

## Browser risks
- Session crash → recreate browser, requeue task
- Memory leaks → restart browser every N tasks
- TTL mismatch → validate final review before submit

## Form risks
- DOM variability → conservative selectors
- Dropdown mismatch → never guess
- Upload failure → validate file attached

## Security risks
- noVNC exposure → auth + signed tokens
- Approval link reuse → one-time tokens
