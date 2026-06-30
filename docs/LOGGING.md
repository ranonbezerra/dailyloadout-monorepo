# Logging

Slate emits structured logs from the API, workers, and operational services.
Production logs are JSON lines, ready for CloudWatch Logs or any log shipper.
Development and tests use a compact console renderer.

## Runtime

- `APP_ENV=production` enables JSON rendering.
- `LOG_LEVEL=INFO` is the default. Use `DEBUG` only for short-lived debugging.
- Each API request receives or propagates `X-Request-ID`; the same value is
  returned in the response header and bound to all logs emitted during the
  request.

## Standard Fields

All application logs include:

- `timestamp`, `level`, `event`, `logger`
- `service`, `app_env`
- `request_id`, `method`, `path`, `client_ip`, `user_public_id` for request logs
- `job_id`, `job_name` for background jobs
- Domain identifiers such as `user_id`, `pick_id`, `play_session_id`, `capture_id`

## PII Policy

Do not log secrets, tokens, prompts, raw LLM text, raw wrap-ups, passwords, or
full email addresses.

Allowed identifiers:

- Internal numeric IDs for server-side correlation.
- Public UUIDs when they are already part of the API surface.
- Email hashes for auth failures or registration rejects.
- Email domains for deliverability/security checks.

## Severity Policy

- `info`: expected request, job, and domain lifecycle events.
- `warning`: security signals, rate limits, registration rejects, refresh-token
  reuse, Turnstile failures, and audited backoffice mutations.
- `error`: unhandled request failures, failed jobs, and exceptions that require
  operator attention.

## Event Catalog

HTTP:

- `http_request_completed`
- `http_request_failed`
- `rate_limit_exceeded`

Auth and security:

- `auth_register_succeeded`
- `auth_register_rejected`
- `auth_login_succeeded`
- `auth_login_failed`
- `auth_refresh_rotated`
- `auth_logout`
- `auth_sessions_revoked`
- `auth_user_banned`
- `refresh_token_reuse_detected`
- `turnstile_token_missing`
- `turnstile_verify_failed`
- `email_rejected`

Domain:

- `pick_requested`
- `pick_created`
- `pick_actioned`
- `play_session_started`
- `recap_generated`
- `wrap_up_extraction_dispatched`
- `wrap_up_extraction_started`
- `wrap_up_extraction_completed`
- `capture_processing_started`
- `capture_review_ready`
- `capture_processing_failed`

Jobs:

- `job_started`
- `job_completed`
- `job_failed`
- `play_session_auto_clamped`
- `pick_auto_ignored`
- `library_import_processed`
- `library_import_failed`

Backoffice:

- `admin_user_banned`
- `admin_user_unbanned`
- `admin_user_verified`
- `admin_config_set`
- `admin_config_cleared`
- `admin_game_demoted`
- `admin_game_promoted`
- `admin_game_edited`
- `admin_capture_reprocessed`
- `admin_capture_purged`
- `admin_play_session_clamped`

## CloudWatch Alarms

The first production dashboard should derive alarms from logs before adding a
separate metrics stack. Recommended initial alarms:

| Alarm | Filter | Window | Action |
| --- | --- | --- | --- |
| API 5xx spike | `event = "http_request_completed" and status_code >= 500` | 5 minutes | Page/check deploy |
| Request exceptions | `event = "http_request_failed"` | 5 minutes | Page/check app logs |
| Refresh-token reuse | `event = "refresh_token_reuse_detected"` | 1 minute | Security review |
| Failed jobs | `event = "job_failed"` grouped by `job_name` | 5 minutes | Check worker health |
| Rate-limit spike | `event = "rate_limit_exceeded"` grouped by `path` | 5 minutes | Abuse/cost review |
| Auth failure spike | `event = "auth_login_failed"` grouped by `email_hash` or `client_ip` | 5 minutes | Abuse review |
| Turnstile failures | `event in ["turnstile_token_missing", "turnstile_verify_failed"]` | 5 minutes | Bot/config review |

Metric filters can use the JSON fields directly once ECS/Fargate or another
runtime ships stdout to a CloudWatch log group.

## CloudWatch Logs Insights

Trace one request:

```sql
fields @timestamp, level, event, path, status_code, duration_ms
| filter request_id = "REQ_ID_HERE"
| sort @timestamp asc
```

Slow API requests:

```sql
fields @timestamp, method, path, status_code, duration_ms, request_id
| filter event = "http_request_completed" and duration_ms >= 1000
| sort duration_ms desc
| limit 50
```

5xx errors by path:

```sql
fields path, status_code
| filter event = "http_request_completed" and status_code >= 500
| stats count(*) as errors by path, status_code
| sort errors desc
```

Auth/security review:

```sql
fields @timestamp, event, reason, email_hash, user_id, client_ip, path
| filter event in [
  "auth_login_failed",
  "auth_register_rejected",
  "refresh_token_reuse_detected",
  "turnstile_verify_failed",
  "rate_limit_exceeded"
]
| sort @timestamp desc
| limit 100
```

Failed jobs:

```sql
fields @timestamp, job_name, job_id, event, duration_ms, capture_id, play_session_id
| filter event = "job_failed"
| sort @timestamp desc
| limit 50
```

Backoffice mutations:

```sql
fields @timestamp, event, admin_public_id, admin_action, target_public_id, resource_type
| filter event like /^admin_/
| sort @timestamp desc
| limit 100
```
