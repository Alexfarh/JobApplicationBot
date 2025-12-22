# System Overview (V1)

This system automates job applications using a queue-based runner and a single remote browser session.

## High-level flow

1. User creates an ApplicationRun with job URLs
2. Runner processes tasks sequentially
3. If auth/setup required → task moves to NEEDS_AUTH
4. If final review reached → task moves to PENDING_APPROVAL
5. User approves → submission occurs
6. Runner continues until batch complete

## Why this architecture
- Prevents babysitting
- Allows safe recovery from failures
- Keeps browser state consistent
- Matches real-world ATS constraints
