# Data Model (V1)

## application_runs
- id (uuid)
- user_id
- status: running | paused | stopped | completed
- settings_snapshot (jsonb)
- batch_size
- created_at
- updated_at

## job_postings
- id
- source
- job_url
- apply_url
- company_name
- job_title
- location_text
- work_mode
- employment_type
- industry
- description_raw
- description_clean

## application_tasks (QUEUE UNIT)
- id
- run_id
- job_id
- state
- priority
- attempt_count
- last_error_code
- last_error_message
- queued_at
- started_at
- last_state_change_at

### Allowed states
QUEUED, RUNNING, NEEDS_AUTH, NEEDS_USER,  
PENDING_APPROVAL, APPROVED, SUBMITTED, FAILED, EXPIRED

Indexes:
- (run_id, state, priority desc, queued_at asc)
- UNIQUE(run_id, job_id)

## remote_browser_sessions
- id
- run_id
- status
- provider
- user_console_url
- started_at
- last_heartbeat_at
- expires_at

## form_captures
- id
- task_id
- captured_at
- fields (jsonb array)

## approval_requests
- id
- task_id
- status
- channel
- approval_token
- created_at
- expires_at
- approved_at
