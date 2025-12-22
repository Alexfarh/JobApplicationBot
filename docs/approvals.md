# Approval System (V1)

## When approvals are used
- Platform has no draft/save
- Bot reaches final review step

## Flow
1. Capture form answers
2. Create ApprovalRequest (TTL 20 min)
3. Send email with approval link
4. On approve → submit using same session

## Expiry
- Approval after TTL → EXPIRED
- Requires rerun

## Channels
- Email only (V1)
