# Slate — API Reference

The Slate API is a REST API built with FastAPI. Full interactive documentation is available at runtime via the Scalar UI.

---

## Interactive docs

Start the API and open:

```text
http://localhost:8100/docs
```

This serves the [Scalar](https://scalar.com) API reference, generated from the OpenAPI spec. You can explore endpoints, see request/response schemas, and test requests directly from the browser.

The raw OpenAPI spec is available at:

```text
http://localhost:8100/openapi.json
```

---

## Authentication

All endpoints except `/health` and `/auth/*` require a Bearer token.

### Register

```http
POST /v1/auth/register
Content-Type: application/json

{
  "email": "player@example.com",
  "password": "securepassword",
  "display_name": "Player One"
}
```

### Login

```http
POST /v1/auth/login
Content-Type: application/json

{
  "email": "player@example.com",
  "password": "securepassword"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### Using the token

```http
Authorization: Bearer eyJ...
```

Access tokens expire in 15 minutes. Use the refresh token to obtain a new one:

```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "..."
}
```

---

## Endpoint groups

### Health

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Returns `{"status": "ok"}` |

### Auth (`/v1/auth`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/register` | Create account |
| POST | `/login` | Get access + refresh tokens |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Revoke refresh token |
| POST | `/logout-all` | Revoke every session (token_version bump) |
| GET | `/sessions` | List the caller's active sessions (devices) |
| DELETE | `/sessions/{public_id}` | Revoke one session by handle (owner-scoped) |
| GET | `/me` | Current user profile |
| GET | `/me/export` | Export the caller's personal data (GDPR/LGPD portability) |
| POST | `/delete-account` | Permanently erase the account (password re-auth; GDPR/LGPD erasure) |

The auth surface also includes (see the live `/docs` for schemas):

- **Email verification & password recovery** — `/v1/auth/verify-email`, `/v1/auth/forgot-password`, `/v1/auth/reset-password`, `/v1/auth/change-password` (single-use, session-invalidating reset tokens).
- **Email change** — `POST /v1/auth/change-email` (password re-auth → confirm link to the new address, notice to the old) then `POST /v1/auth/confirm-email-change` (token-gated).
- **Two-factor (TOTP)** — `/v1/auth/mfa/*` (`status`, `enroll`, `confirm`, challenge/verify, disable; encrypted-at-rest secrets + single-use recovery codes).
- **Social login (OAuth)** — `GET /v1/auth/oauth/{provider}/start` and `/callback` (Google, Twitch; Authorization Code + PKCE).

### Library (`/v1`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/platforms` | List all platforms |
| POST | `/games` | Create a game manually |
| PATCH | `/games/{public_id}` | Update a game (e.g. genres) |
| GET | `/games/search?q=` | Search games by title |
| GET | `/games/genres` | List all distinct genres |
| GET | `/library` | List user's library entries |
| POST | `/library` | Add game to library |
| PATCH | `/library/{public_id}` | Update library entry |
| DELETE | `/library/{public_id}` | Delete library entry |

### Captures (`/v1/captures`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/text` | Submit text capture |
| POST | `/voice` | Submit voice capture (multipart) |
| POST | `/photo` | Submit photo capture (multipart) |
| GET | `/{public_id}` | Get capture status + candidates |
| POST | `/{public_id}/candidates/{cid}/confirm` | Confirm a candidate |
| POST | `/{public_id}/candidates/{cid}/reject` | Reject a candidate |
| POST | `/library-import` | Bulk import from platform screenshots (multipart, multiple images) |
| GET | `/{public_id}/candidates/duplicates` | List candidates that duplicate existing library entries |
| POST | `/{public_id}/candidates/bulk-confirm` | Confirm many candidates, reject the rest, in one call |
| POST | `/{public_id}/candidates/{cid}/rematch` | Re-match a candidate to a corrected title (re-search IGDB) |

### PlaySessions (`/v1/play-sessions`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/` | Start a play session |
| GET | `/active` | Get active play session |
| POST | `/{public_id}/wrap-up` | Submit wrap-up text |
| POST | `/{public_id}/end` | End play session without wrap-up |
| POST | `/{public_id}/recap/preview` | Preview recap before starting |
| POST | `/{public_id}/recap/regenerate` | Regenerate recap |

Recap requests accept a `mode`: `quick` (single-shot, grounded on the player's own
history), `deep` (LangGraph web-research path), or `auto` (**Smart recap**, Epic 29) — the
server grades whether the retrieved local history is rich enough and routes `quick`/`deep`
itself. A brand-new game with no history stays `quick` (cold-start cost guard), and a
free-tier user is never auto-escalated to the paid `deep` path (entitlement gate); `deep`
remains available as an explicit override.

### Picks (`/v1/picks`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/` | Create pick suggestion(s) |
| GET | `/` | List picks (paginated) |
| GET | `/latest` | Get latest pending pick |
| POST | `/{public_id}/accept` | Accept and start play session |
| POST | `/{public_id}/reject` | Reject suggestion |

### Stats (`/v1/stats`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/overview` | KPI summary (games, play sessions, durations) |
| GET | `/sessions` | Recent sessions (paginated) |

### Concierge (`/v1/concierge`)

Tool-using conversational agent over the real library and play-session pipeline (opt-in; gated write tools are UUID-validated).

| Method | Path | Description |
| --- | --- | --- |
| POST | `/chat` | Send a message; streamed reply (SSE) keyed by a thread id |

### Backoffice (`/internal/v1`)

Internal admin surface. Every route requires a backoffice admin grant
(`admin_users` table — never a JWT claim, re-checked on each request). The
`/internal` prefix is non-advertising so the reverse proxy can deny it from the
public origin; single-user mode is rejected outright. Non-admins get `403`.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/me` | Current admin identity (panel access check) |
| GET | `/dashboard` | Aggregate metrics (user/ban/verify/admin counts, active sessions, catalogue size, config overrides, recent actions) |
| GET | `/users` | List/search users — `q`, `banned`, `verified`, `limit`, `offset` |
| GET | `/users/{public_id}` | Full user detail (sessions, admin/password flags) |
| POST | `/users/{public_id}/ban` | Ban + kill sessions; body `{ "reason": str? }`; refuses admins |
| POST | `/users/{public_id}/unban` | Lift a ban (does not re-mint sessions) |
| POST | `/users/{public_id}/verify` | Force-verify the user's email (idempotent) |
| GET | `/games` | List/search catalogue — `q`, `source`, owner counts + provenance |
| GET | `/games/{public_id}` | Game detail (metadata, provenance, owner count) |
| POST | `/games/{public_id}/demote` | Demote a shared game to private (surfaces `demote_game.py`) |
| POST | `/games/{public_id}/promote` | Promote a game back to shared |
| PATCH | `/games/{public_id}` | Edit catalogue metadata (title, summary) |
| GET | `/captures` | List/search captures with per-status tallies — `q`, `status` |
| GET | `/captures/{public_id}` | Capture detail + candidates |
| POST | `/captures/{public_id}/reprocess` | Re-run the capture pipeline (rate-limited + cost-guarded) |
| DELETE | `/captures/{public_id}` | Purge a capture |
| GET | `/play-sessions` | List/search play sessions with per-status tallies — `q`, `status` |
| GET | `/play-sessions/{public_id}` | Play-session detail |
| POST | `/play-sessions/{public_id}/clamp` | Force-end an active session (`ended_via=admin_clamp`) |
| GET | `/picks` | List/search picks with per-action tallies — `q`, `action` (read-only) |
| GET | `/picks/{public_id}` | Pick detail (read-only) |
| POST | `/cache/flush` | Break-glass: flush every application-cache namespace + the in-process tier (rate-limited, audited; durable rate-limit/cost counters untouched) |
| GET | `/config` | List the curated operational knobs (effective/override/baseline) |
| PUT | `/config/{key}` | Set a runtime override (validated); `422` on bad type/range, `404` unknown key |
| DELETE | `/config/{key}` | Clear the override, reverting to the env/code baseline |
| GET | `/audit` | Audited admin actions, newest first (`limit`, `offset`) |

Every mutation appends an `admin_audit_log` row (actor, action, target, optional reason).

**Dynamic config** (`/config`): a curated set of operational knobs — kill-switches
(`rate_limit_enabled`, `cost_guard_enabled`, `concierge_write_tools_enabled`), abuse
caps (`cost_user_per_day`, `cost_global_per_day`, `rate_limit_register_per_minute`,
`igdb_user_budget_per_day`), and product rules (`catalog_share_threshold`,
`block_disposable_emails`) — overridable at **runtime without a redeploy**. Precedence
is **override (Postgres `app_config`) > env var > code default**; the change is read by
consumers within a short cache TTL. Secrets/infra stay env-only. `PUT` body is
`{ "value": <bool|int> }`.

---

## Common patterns

### Pagination

List endpoints accept `limit` and `offset` query parameters:

```http
GET /v1/library?limit=20&offset=0
GET /v1/stats/sessions?limit=10&offset=0
```

Responses include `total`, `limit`, and `offset` fields.

### Filtering

Library entries can be filtered by status:

```http
GET /v1/library?status=playing
```

### Error responses

Errors follow a consistent format:

```json
{
  "detail": "Library entry not found"
}
```

| Status | Meaning |
| --- | --- |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 404 | Resource not found |
| 409 | Conflict (duplicate, already exists) |
| 422 | Unprocessable (e.g. LLM failed after retries) |
| 429 | Rate limited |

---

## Rate limiting

Rate limits are enforced across the API (backed by Redis, shared across workers):

- **Auth routes** are IP- **and** target-account-limited (login, register, verification resend, OAuth start/callback) to blunt brute-force and distributed attacks on a single account.
- **Expensive routes** are per-user limited — e.g. concierge chat, recap, pick, capture, and library-import each have their own cap.
- A generous **per-user backstop** applies to every authenticated request as a catch-all.
- Limiters **fail open** (a Redis outage allows the request, logged) except on account-creation surfaces, which fail closed.
- On top of rate limits, LLM-bearing routes pass through a **cost guard** (per-user + global token→$ spend caps) that returns `429`/`503` when a ceiling is hit.

Per-route caps are tunable at runtime via the backoffice operational config. Exceeding a limit returns `429` with a `Retry-After` header.

---

## CORS

Allowed origins are configured via the `CORS_ORIGINS` environment variable. Default in development:

```env
CORS_ORIGINS=["http://localhost:3200","http://localhost:5173"]
```
