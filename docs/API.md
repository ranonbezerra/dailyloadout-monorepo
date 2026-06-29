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
| GET | `/me` | Current user profile |

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

### PlaySessions (`/v1/play-sessions`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/` | Start a play session |
| GET | `/active` | Get active play session |
| POST | `/{public_id}/wrap-up` | Submit wrap-up text |
| POST | `/{public_id}/end` | End play session without wrap-up |
| POST | `/{public_id}/recap/preview` | Preview recap before starting |
| POST | `/{public_id}/recap/regenerate` | Regenerate recap |

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

### Backoffice (`/internal/v1`)

Internal admin surface. Every route requires a backoffice admin grant
(`admin_users` table — never a JWT claim, re-checked on each request). The
`/internal` prefix is non-advertising so the reverse proxy can deny it from the
public origin; single-user mode is rejected outright. Non-admins get `403`.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/me` | Current admin identity (panel access check) |
| GET | `/users` | List/search users — `q`, `banned`, `verified`, `limit`, `offset` |
| GET | `/users/{public_id}` | Full user detail (sessions, admin/password flags) |
| POST | `/users/{public_id}/ban` | Ban + kill sessions; body `{ "reason": str? }`; refuses admins |
| POST | `/users/{public_id}/unban` | Lift a ban (does not re-mint sessions) |
| POST | `/users/{public_id}/verify` | Force-verify the user's email (idempotent) |
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
| 429 | Rate limited (auth endpoints) |

---

## Rate limiting

Auth endpoints (`/v1/auth/login`, `/v1/auth/register`) are rate-limited to prevent brute-force attacks. Other endpoints are not rate-limited in v1.0.

---

## CORS

Allowed origins are configured via the `CORS_ORIGINS` environment variable. Default in development:

```env
CORS_ORIGINS=["http://localhost:3200","http://localhost:5173"]
```
