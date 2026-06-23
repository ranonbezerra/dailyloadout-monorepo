# DailyLoadout — Architecture

This document is the technical companion to [PRODUCT.md](./PRODUCT.md). It covers stack decisions, schema, module structure, critical flows, and the rationale behind non-obvious choices.

---

## 1. Repository layout

```
dailyloadout-monorepo/
├── README.md
├── PRODUCT.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── Makefile                        # orchestrates all commands from root
├── docker-compose.yml              # postgres + redis + ollama
├── docker-compose.dev.yml          # hot-reload overrides for dev
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci-api.yml              # pytest + ruff + mypy
│       ├── ci-app.yml              # flutter analyze + flutter test
│       └── ci-web.yml              # bun test + biome
├── packages/
│   ├── api/                        # FastAPI backend
│   ├── app/                        # Flutter mobile client (iOS + Android)
│   └── web/                        # Bun + React + Mantine dashboard
├── infra/
│   ├── ollama/                     # Custom Modelfiles, model pull scripts
│   └── postgres/                   # init.sql, extensions bootstrap
└── docs/
    ├── DEPLOYMENT.md               # Fly.io, Railway, Hetzner VPS
    ├── OLLAMA.md                   # Models, VRAM, CPU fallbacks
    └── API.md                      # Points to /docs (Scalar)
```

**Why monorepo:** the recruiter (and future contributors) clones one repo and sees the full system. Three separate repos would force them to clone three things and guess at the wiring. Tooling cost is minimal (workspaces are not needed across stacks — each package owns its own build).

---

## 2. Stack — final consolidated

### 2.1 `packages/api/` — FastAPI backend

- **Python 3.14** (managed via Poetry)
- **FastAPI** 0.115+
- **Pydantic v2** for schemas
- **SQLAlchemy 2.x async** + **Alembic** for migrations
- **PostgreSQL 18** with `citext`, `pg_trgm`, `pgcrypto` extensions
- **Redis 7** for IGDB cache, refresh-token denylist, job queue
- **arq** for async background jobs (chosen over Celery for async-native fit with FastAPI)
- **fastapi-users** for authentication (email/password + optional Google OAuth)
- **slowapi** for rate limiting on `/auth/*`
- **faster-whisper** for local speech-to-text
- **structlog** + JSON logs
- **Sentry** SDK (env-gated, opt-in)
- **ruff** for lint + format, **mypy** for types
- **pytest** + **pytest-asyncio** + **factory-boy** for tests

**Why FastAPI for both API and AI orchestration:** the AI workload is "thin" — call Ollama, validate output, persist. No fine-tuning, no model serving, no GPU pipeline. Splitting into a separate NestJS API and Python AI engine adds inter-service communication overhead with no real boundary benefit at this scale. A clean `infrastructure/llm/` module inside FastAPI carries the AI concern; if a future product needs the same briefing engine, then it gets extracted. YAGNI until then.

### 2.2 `packages/app/` — Flutter mobile client

- **Flutter 3.27+ / Dart 3.6+**
- **BLoC** (`bloc` ^9 + `flutter_bloc` ^9 + `bloc_concurrency` ^0.3 + `bloc_test` for tests) — chosen for consistency with author's other Flutter codebases
- **equatable** ^2 for BLoC events/states
- **formz** ^0.8 for form validation
- **go_router** for declarative navigation (modern alternative to the Navigator 1.0 pattern used in older codebases)
- **dio** for HTTP, with interceptors for auth refresh
- **flutter_secure_storage** for refresh tokens
- **flutter_dotenv** for envs
- **record** ^5 for audio capture
- **image_picker** ^1 for photos
- **fl_chart** for in-app charts
- **cached_network_image**, **shimmer**, **flutter_svg** for UI polish
- **sentry_flutter** (env-gated)
- **uuid**, **logger**, **intl**

Target platforms: **iOS, Android.** Desktop users are served by the web dashboard (`packages/web/`).

### 2.3 `packages/web/` — React dashboard

- **Bun** as runtime and package manager
- **Vite** as bundler
- **React 19** + **TypeScript 5.x**
- **Mantine v8** as UI framework (DataTable, Charts, Forms, Notifications)
- **TanStack Query** for server state
- **react-router-dom v7** for routing
- **react-hook-form** + **zod** for forms
- **dayjs** for dates
- **openapi-typescript** for generating typed client from the API's OpenAPI spec

**Why Mantine over shadcn/ui:** the web is primarily a dashboard with data tables and charts. Mantine ships these as first-class components (`mantine-datatable`, Mantine Charts wrapping Recharts). shadcn/ui shines for hand-crafted SaaS marketing UI; Mantine shines for admin/analytics, which matches the use case here.

### 2.4 Infrastructure

- **Docker Compose** for local dev and self-hosting
- **Ollama** as the LLM runtime
- **GitHub Actions** for CI per package
- **MIT** license

---

## 3. Database schema

PostgreSQL 18 with these extensions, created in `infra/postgres/init.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS citext;       -- case-insensitive emails
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- trigram fuzzy search on titles
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()
```

**ID strategy:** internal IDs are `bigserial` (fast joins, small indexes). External IDs are `uuid` columns named `public_id`, exposed to clients. This hides cardinality and is enumeration-safe, without sacrificing internal performance.

### 3.1 `users`

```sql
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    public_id       UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    email           CITEXT NOT NULL UNIQUE,
    password_hash   TEXT,                       -- nullable: OAuth-only users
    display_name    TEXT NOT NULL,
    avatar_url      TEXT,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    locale          TEXT NOT NULL DEFAULT 'pt-BR',
    timezone        TEXT NOT NULL DEFAULT 'America/Recife',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_users_email_active ON users(email) WHERE deleted_at IS NULL;
```

### 3.2 `oauth_identities`

```sql
CREATE TABLE oauth_identities (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL,              -- 'google' (extensible)
    provider_uid    TEXT NOT NULL,
    email           CITEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_uid)
);

CREATE INDEX idx_oauth_user ON oauth_identities(user_id);
```

### 3.3 `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,       -- SHA-256 of token; raw never stored
    device_label    TEXT,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ
);

CREATE INDEX idx_refresh_user_active ON refresh_tokens(user_id) WHERE revoked_at IS NULL;
```

### 3.4 `games` (canonical)

```sql
CREATE TABLE games (
    id                  BIGSERIAL PRIMARY KEY,
    public_id           UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    slug                TEXT NOT NULL UNIQUE,           -- dedupe key
    title               TEXT NOT NULL,
    igdb_id             BIGINT UNIQUE,                  -- nullable: manual games
    summary             TEXT,
    cover_url           TEXT,
    first_release_date  DATE,
    genres              TEXT[],
    metadata_source     TEXT NOT NULL,                  -- 'igdb' | 'manual' | 'llm_extracted'
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_games_title_trgm ON games USING gin (title gin_trgm_ops);
```

### 3.5 `platforms`

```sql
CREATE TABLE platforms (
    id      SMALLSERIAL PRIMARY KEY,
    slug    TEXT NOT NULL UNIQUE,       -- 'switch', 'ps5', 'pc-steam'
    label   TEXT NOT NULL,
    family  TEXT NOT NULL               -- 'nintendo' | 'sony' | 'pc' | 'xbox' | 'mobile'
);
```

Seeded via migration: Switch, PS5, PS4, Xbox Series, PC-Steam, PC-GOG, PC-Epic, iOS, Android, Other.

### 3.6 `library_entries`

```sql
CREATE TYPE library_status AS ENUM ('backlog', 'playing', 'paused', 'completed', 'dropped');

CREATE TABLE library_entries (
    id                  BIGSERIAL PRIMARY KEY,
    public_id           UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id             BIGINT NOT NULL REFERENCES games(id),
    platform_id         SMALLINT NOT NULL REFERENCES platforms(id),
    status              library_status NOT NULL DEFAULT 'backlog',
    acquired_at         DATE,
    last_played_at      TIMESTAMPTZ,
    mission_next_action TEXT,           -- denormalized; updated by debrief_processor
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, game_id, platform_id)
);

CREATE INDEX idx_library_user_status ON library_entries(user_id, status);
CREATE INDEX idx_library_user_last_played ON library_entries(user_id, last_played_at DESC NULLS LAST);
```

### 3.7 `missions`

```sql
CREATE TYPE mission_ended_via AS ENUM (
    'debrief_completed',
    'paused_app',
    'auto_clamp_8h',
    'cancelled'
);

CREATE TABLE missions (
    id                  BIGSERIAL PRIMARY KEY,
    public_id           UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    library_entry_id    BIGINT NOT NULL REFERENCES library_entries(id) ON DELETE CASCADE,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at            TIMESTAMPTZ,
    ended_via           mission_ended_via,
    briefing_text       TEXT,
    debrief_text        TEXT,
    extracted_state     JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Global constraint: one active mission per user.
CREATE UNIQUE INDEX idx_missions_one_active_per_user
    ON missions(user_id) WHERE ended_at IS NULL;

CREATE INDEX idx_missions_user_recent ON missions(user_id, started_at DESC);
CREATE INDEX idx_missions_library_entry ON missions(library_entry_id, started_at DESC);
```

**Why `user_id` is denormalized on `missions`:** the partial unique index above requires the column to live on the same table. Without this denormalization, the "one active mission per user" rule would be application-only — a race condition could create two. Trade-off: a small write-time cost (must keep `user_id` consistent with `library_entries.user_id`) for an absolute database-level guarantee.

### 3.8 `captures` and `capture_candidates`

```sql
CREATE TYPE capture_status AS ENUM (
    'queued', 'processing', 'review',
    'partially_committed', 'committed',
    'failed', 'cancelled'
);

CREATE TYPE capture_input_type AS ENUM ('voice', 'photo', 'text', 'manual');

CREATE TABLE captures (
    id              BIGSERIAL PRIMARY KEY,
    public_id       UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    input_type      capture_input_type NOT NULL,
    status          capture_status NOT NULL DEFAULT 'queued',
    raw_text        TEXT,
    raw_audio_key   TEXT,                       -- storage path; nulled on terminal state
    raw_image_key   TEXT,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_captures_user_recent ON captures(user_id, created_at DESC);
CREATE INDEX idx_captures_status ON captures(status) WHERE status IN ('queued', 'processing');

CREATE TYPE candidate_status AS ENUM ('pending', 'confirmed', 'rejected', 'skipped');

CREATE TABLE capture_candidates (
    id                      BIGSERIAL PRIMARY KEY,
    capture_id              BIGINT NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
    detected_title          TEXT NOT NULL,
    suggested_game_id       BIGINT REFERENCES games(id),
    suggested_platform_id   SMALLINT REFERENCES platforms(id),
    confidence              REAL,
    status                  candidate_status NOT NULL DEFAULT 'pending',
    library_entry_id        BIGINT REFERENCES library_entries(id),
    user_note               TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at             TIMESTAMPTZ
);

CREATE INDEX idx_candidates_capture ON capture_candidates(capture_id);
CREATE INDEX idx_candidates_pending ON capture_candidates(capture_id) WHERE status = 'pending';
```

**Why a dedicated `capture_candidates` table** (instead of a JSONB column on `captures`): candidates need individual state — user may confirm some, skip others. The `partially_committed` status of a capture is derived from the mix of candidate statuses. JSONB would force application-level mutation logic and lose the indexability and integrity of per-candidate operations.

### 3.9 `loadouts`

```sql
CREATE TYPE loadout_action AS ENUM ('accepted', 'rejected', 'ignored', 'pending');

CREATE TABLE loadouts (
    id                          BIGSERIAL PRIMARY KEY,
    public_id                   UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    user_id                     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mood                        TEXT NOT NULL,
    available_minutes           INT NOT NULL,
    mental_energy               TEXT NOT NULL,
    suggested_library_entry_id  BIGINT REFERENCES library_entries(id),
    reasoning                   TEXT NOT NULL,
    action                      loadout_action NOT NULL DEFAULT 'pending',
    resulting_mission_id        BIGINT REFERENCES missions(id),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at                 TIMESTAMPTZ
);

CREATE INDEX idx_loadouts_user_recent ON loadouts(user_id, created_at DESC);
```

### 3.10 `audit_log`

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,              -- 'mission.start', 'library_entry.delete'
    target_type TEXT NOT NULL,
    target_id   BIGINT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_user_recent ON audit_log(user_id, created_at DESC);
```

Used by the web dashboard for the activity timeline.

---

## 4. API module structure

```
packages/api/
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── src/
│   └── dailyloadout/
│       ├── main.py                 # FastAPI app factory + lifespan
│       ├── config.py               # Pydantic Settings (envs)
│       ├── deps.py                 # FastAPI dependencies (get_db, get_current_user)
│       ├── api/v1/
│       │   ├── auth.py
│       │   ├── library.py
│       │   ├── games.py
│       │   ├── captures.py
│       │   ├── missions.py
│       │   ├── loadouts.py
│       │   ├── stats.py
│       │   └── admin.py            # web dashboard endpoints
│       ├── core/                   # domain layer
│       │   ├── auth/
│       │   ├── library/
│       │   ├── capture/
│       │   ├── mission/
│       │   ├── loadout/
│       │   └── stats/
│       ├── infrastructure/
│       │   ├── db/
│       │   │   ├── models.py           # SQLAlchemy models
│       │   │   ├── session.py
│       │   │   └── repositories/
│       │   ├── llm/
│       │   │   ├── base.py             # AbstractLLMClient
│       │   │   ├── ollama_client.py
│       │   │   ├── bedrock_client.py   # optional
│       │   │   ├── dummy_client.py
│       │   │   └── factory.py
│       │   ├── stt/
│       │   │   ├── base.py
│       │   │   ├── whisper_local.py    # faster-whisper
│       │   │   ├── dummy_client.py
│       │   │   └── factory.py
│       │   ├── storage/
│       │   │   ├── base.py
│       │   │   ├── local_fs.py
│       │   │   ├── s3.py
│       │   │   └── factory.py
│       │   ├── igdb/client.py          # opt-in via env
│       │   └── email/smtp.py           # opt-in via env
│       ├── workers/
│       │   ├── arq_settings.py
│       │   ├── capture_processor.py
│       │   ├── mission_auto_clamp.py
│       │   ├── debrief_processor.py
│       │   └── briefing_warmer.py
│       └── prompts/
│           ├── capture_parse.j2
│           ├── capture_parse_vision.j2
│           ├── briefing.j2
│           ├── loadout.j2
│           └── debrief_extract.j2
└── tests/
    ├── conftest.py
    ├── factories.py
    ├── unit/
    └── integration/
```

**Architectural pattern:** ports & adapters (hexagonal), pragmatic. `core/` defines interfaces and domain use cases. `infrastructure/` implements them. `api/` adapts HTTP. No heavy DI container — FastAPI `Depends` + factory pattern handles everything. The same pattern carries through every external concern: LLM, STT, storage, email, IGDB — each has an abstract base, one real implementation, one dummy for tests, and a factory that picks one based on environment variables.

---

## 5. Critical flows

### 5.1 Capture (any input type)

```
Client                  API                       arq worker            External
  |                      |                            |                     |
  |--POST /captures----->|                            |                     |
  |                      |--save raw to storage------>|                     |
  |                      |--insert capture queued---->|                     |
  |                      |--enqueue job-------------->|                     |
  |<--202 + public_id----|                            |                     |
  |                                                   |                     |
  |                                                   |--STT (if voice)---->| Whisper
  |                                                   |--LLM parse--------->| Ollama
  |                                                   |--enrich (per cand)->| IGDB
  |                                                   |--insert candidates  |
  |                                                   |--status=review      |
  |                                                   |--delete raw         |
  |                                                                         |
  |--GET /captures/{id}->|                                                  |
  |<--status, candidates|                                                  |
  |                      |                                                  |
  |--POST candidate/confirm->|                                              |
  |                          |--create library_entry                        |
  |                          |--candidate=confirmed                         |
  |                          |--capture status recompute                    |
  |<--200--------------------|                                              |
```

**Idempotency:** the worker is idempotent. Re-running `capture_processor` on a stuck capture is safe — state machine prevents double-processing. Recovery from a crashed worker is automatic via arq's retry policy.

### 5.2 Briefing (anti-hallucination flow)

```
1. User taps "Start Mission" on LibraryEntry X.
2. API validates: user has no other active mission (partial unique index).
3. API creates mission row.
4. API queries:
       SELECT * FROM missions
        WHERE library_entry_id = X
          AND user_id = current_user
          AND ended_via = 'debrief_completed'
          AND extracted_state IS NOT NULL
        ORDER BY started_at DESC
        LIMIT 3
5. API renders prompts/briefing.j2 with those debriefs + entry.mission_next_action.
6. API calls Ollama (smart model).
7. ANTI-HALLUCINATION CHECK:
       - Tokenize output: proper nouns, capitalized terms, numbers
       - Tokenize input context same way
       - Compute overlap = |output_tokens ∩ input_tokens| / |output_tokens|
       - If overlap < 0.7: log 'suspicious_briefing', set flag in response
8. Save briefing_text on mission. Return to app.
```

**Why this is in the database, not just the application:** the partial unique index enforces "one active mission" at the storage layer. Even a buggy app or a malicious direct DB write cannot violate the invariant. The application logic is redundant defense, not the primary guard.

### 5.3 Daily Loadout (UUID validation flow)

```
1. POST /v1/loadouts {mood, available_minutes, mental_energy}
2. API queries eligible library_entries:
       status IN ('backlog', 'playing', 'paused')
       AND NOT EXISTS (
           SELECT 1 FROM missions m
           WHERE m.library_entry_id = library_entries.id
             AND m.ended_at > now() - interval '12 hours'
       )
3. Render prompts/loadout.j2 with candidate list + user context.
4. Call Ollama (smart model). Expect {"library_entry_public_id": "...", "reasoning": "..."}.
5. VALIDATION:
       - Does returned public_id exist in candidate list?
       - If NO: reroll once with stricter prompt.
       - If second attempt also invalid: return 422 to client.
6. If valid: create loadout row with action='pending'.
7. Return suggestion + reasoning to app.
```

The validation step is **deterministic** layered on top of probabilistic LLM output. No retraining, no fine-tuning — just an explicit guardrail.

### 5.4 Debrief extraction (async-first with sync fallback)

```
Client                  API                     Taskiq worker          External
  |                      |                            |                     |
  |--PATCH debrief------>|                            |                     |
  |                      |--save debrief_text         |                     |
  |                      |--end mission               |                     |
  |                      |--dispatch task------------>|                     |
  |<--200 (instant)------|                            |                     |
  |                                                   |                     |
  |                                                   |--LLM extract------->| Ollama
  |                                                   |--set extracted_state|
  |                                                   |--update next_action |
  |                                                   |--commit             |
  |                                                                         |
  |            [Later: user starts next mission]                            |
  |--POST /missions----->|                                                  |
  |                      |--check: previous mission has extracted_state?    |
  |                      |    YES → use it for briefing                     |
  |                      |    NO  → sync fallback: extract now, then brief  |
  |<--201 + briefing-----|                                                  |
```

**Why async:** debrief extraction calls the LLM (1–10s depending on hardware). The user doesn't need the extracted state immediately — it's only consumed when generating the *next* briefing for that game. Blocking the HTTP response for a result the user won't see until their next session is unnecessary latency.

**Why Taskiq:** asyncio-native (tasks are plain `async def`), Redis broker (already in the stack), built-in retry support, actively maintained. Celery lacks async support; arq is maintenance-only.

**Retry with exponential backoff:** the Taskiq worker retries failed extractions up to 3 times with exponential backoff (2s → 4s → 8s). This handles transient Ollama failures without hammering the LLM.

**Sync fallback:** if the worker fails all retries (or hasn't processed yet), `ensure_extractions_complete()` runs the extraction synchronously before generating a briefing. This is a safety net, not the happy path. The user sees a brief loading indicator ("Loading context from your last session...") only in this rare case.

---

## 6. Architectural highlights (for ARCHITECTURE.md readers)

These are the decisions worth a paragraph each, in order of "what differentiates this codebase":

### 6.1 LLM abstraction with multiple backends

`infrastructure/llm/AbstractLLMClient` has four concrete implementations: `OllamaClient` (default), `BedrockClient` (cloud fallback), `DummyLLMClient` (deterministic for tests). Selection is environment-driven. Swapping providers is a config change, not a code change. Tests never call real LLMs.

### 6.2 Deterministic anti-hallucination

LLM outputs are validated against context before persisting or surfacing to the user. Two layers:

- **Token-overlap check** (briefings): tokenize both input and output for proper nouns and numbers; require ≥70% overlap. Below threshold → flag, disclaimer.
- **UUID existence check** (loadouts, structured outputs): any UUID/ID the LLM returns must exist in the candidate set provided to it. Failure → reroll once → 422.

These are deterministic safeguards on probabilistic outputs. No fine-tuning, no model retraining. Cheap to implement, dramatically reduces user-facing hallucination.

### 6.3 State machines for AI workflows

Captures and missions are modeled as explicit state machines, not as boolean flags. Each transition is a method on the domain model with preconditions checked. Workers are idempotent because they consult state before acting. Recovery from partial failure is automatic and explicit, not "hope nothing went wrong."

### 6.4 Database-level invariants over application-level rules

The "one active mission per user" rule is enforced by a partial unique index, not by app code alone. This forces a small denormalization (`user_id` on `missions`) which is documented and justified. The trade-off is conscious: a small write-time cost for an absolute guarantee.

### 6.5 Local-first AI as the default

Ollama for LLM, faster-whisper for STT, multimodal LLM for vision. No cloud key required to run the full stack. Cloud (Bedrock) is opt-in for users who prefer it. This is unusual enough in 2026 to be the defining architectural choice — most AI side projects hard-bind to OpenAI/Anthropic APIs and break the moment the key is missing or the bill is too high.

### 6.6 Same factory + dummy pattern across all external concerns

LLM, STT, storage, email, IGDB — each follows the same shape: abstract base class, real implementation, dummy implementation, factory function. Tests use dummies, prod uses real. The pattern is boring on purpose: anyone reading the codebase understands every external integration the same way after seeing the first one.

### 6.7 Async-first LLM processing with sync fallback

Debrief extraction is fire-and-forget: submit the debrief, end the mission, dispatch a Taskiq task, return instantly. The background worker processes the LLM call with retries and exponential backoff. If the worker fails or hasn't run by the time the data is needed (next briefing), the system falls back to synchronous extraction — the user sees a brief loading state, but never loses data. This pattern ("optimistic background processing, pessimistic on-demand fallback") avoids two failure modes: (1) blocking the user on LLM latency for a result they don't need yet, and (2) silently losing debriefs when the worker is down.

---

## 7. Environment variables (preview)

```env
# Core
APP_ENV=development
SECRET_KEY=change-me-in-prod

# Ports (remapped to avoid conflicts with sibling projects)
POSTGRES_PORT=5433
REDIS_PORT=6380
OLLAMA_PORT=11434
API_PORT=8100
WEB_PORT=3200

# Database
POSTGRES_USER=dailyloadout
POSTGRES_PASSWORD=dailyloadout
POSTGRES_DB=dailyloadout
DATABASE_URL=postgresql+asyncpg://dailyloadout:dailyloadout@localhost:5433/dailyloadout
REDIS_URL=redis://localhost:6380/0

# Single-user mode
SINGLE_USER_MODE=false
SINGLE_USER_EMAIL=

# LLM
LLM_PROVIDER=ollama                  # ollama | bedrock
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_FAST_MODEL=gemma3:4b
OLLAMA_SMART_MODEL=gemma3:12b
LLM_TIMEOUT_SECONDS=60

# STT
STT_PROVIDER=whisper_local           # whisper_local | whisper_api
WHISPER_MODEL=base                   # tiny | base | small | medium

# Storage
STORAGE_PROVIDER=local_fs            # local_fs | s3
STORAGE_LOCAL_PATH=/var/lib/dailyloadout/uploads

# IGDB (optional)
IGDB_CLIENT_ID=
IGDB_CLIENT_SECRET=

# OAuth Google (optional)
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=

# Email (optional)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=DailyLoadout <noreply@dailyloadout.local>

# Limits
CAPTURE_MAX_AUDIO_SECONDS=60
CAPTURE_MAX_IMAGE_MB=10
CAPTURE_MAX_GAMES_PER_SHELF=12
MISSION_AUTO_CLAMP_HOURS=8

# Observability (optional)
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
```

---

## 8. Deployment topology

### 8.1 Local dev / self-hosting (default)

```
┌──────────────────────────────────────────────────────┐
│ Docker Compose (make up)                             │
│                                                      │
│  ┌─────────┐  ┌──────┐  ┌────────┐                   │
│  │postgres │  │redis │  │ollama  │                   │
│  │ :5433   │  │ :6380│  │ :11434 │                   │
│  └────┬────┘  └──┬───┘  └───┬────┘                   │
│       └──────────┴───────────┘                       │
└──────────────────────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────┴────┐    ┌─────┴────┐    ┌─────┴─────┐
│  api    │    │  web     │    │  app      │
│ FastAPI │    │ React    │    │ Flutter   │
│ :8100   │    │ :3200    │    │ (desktop) │
└─────────┘    └──────────┘    └───────────┘
  host process   host process   host process
```

All ports are configurable via `.env`.

### 8.2 Production self-host (Fly.io / Railway)

- API container on a single small VM
- Postgres managed (Fly Postgres, Railway, Supabase)
- Redis managed (Upstash, Fly Redis)
- Ollama on a separate VM with GPU (or CPU if Gemma 4B suffices)
- Storage: S3-compatible (Cloudflare R2, Backblaze B2) when scaling beyond local FS
- Static web hosted on Cloudflare Pages / Netlify pointing at the API

Documented in detail in [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md).

---

## 9. Testing strategy

### 9.1 API

- **Unit tests** — domain logic, state machine transitions, anti-hallucination validators. Coverage target ≥ 85% for `core/`.
- **Integration tests** — endpoints with real Postgres (testcontainers), DummyLLMClient and DummySTTClient. Coverage target ≥ 70% for `api/v1/`.
- **Worker tests** — arq workers with mocked external clients. Idempotency tests (run twice, assert single side effect).
- **Migration tests** — Alembic up/down on each migration.

### 9.2 App

- **Widget tests** — critical screens (auth, library, capture review, briefing).
- **BLoC tests** — `bloc_test` package, every BLoC has at least happy-path and error-path tests.
- **Integration tests** — basic end-to-end on macOS target only (lighter than full mobile matrix).

### 9.3 Web

- **Component tests** — Vitest + React Testing Library for core components.
- **Hook tests** — auth, query hooks.
- **Smoke E2E** — Playwright covering login + library list (no full suite, just guardrail).
