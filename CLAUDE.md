# DailyLoadout — Project Constitution

This file is auto-loaded by Claude Code for every task. It defines the rules, patterns, and constraints that must be followed throughout the codebase.

## Product Summary

DailyLoadout is a gaming companion that helps players choose what to play. It combines a personal game library, AI-powered daily loadout suggestions, structured mission tracking, and analytics — all orchestrated by local LLMs via Ollama.

## Stack

| Package | Path | Stack |
| --------- | ------ | ------- |
| API | `packages/api/` | Python 3.14, FastAPI, SQLAlchemy 2.x async, Alembic, Pydantic v2, Taskiq + Redis, Ollama LLM, faster-whisper STT |
| Mobile | `packages/mobile/` | Flutter 3.27+, Dart 3.6+, BLoC, go_router, dio |
| Web (workspace) | `packages/web/` | Bun workspace. Members below share `@dl/shared` (api client, case-convert). |
| ↳ Shared | `packages/web/shared/` | `@dl/shared` — the cookie-auth API client + snake/camel converters used by both web apps |
| ↳ App (player) | `packages/web/app/` | The player web app. Bun, React 19, TypeScript, Mantine v7, TanStack Query v5, Biome |
| ↳ Backoffice | `packages/web/backoffice/` | Internal admin app (separate from the player app). Same stack; talks to the API's `/internal/v1` |

**Infrastructure:** PostgreSQL 18, Redis 7, Ollama (host), Taskiq worker (Docker)

**Web workspace:** one `bun install` at `packages/web/` resolves all members. The player app and backoffice import the API client from `@dl/shared/api` and `@dl/shared/case-convert` (never duplicate them).

## Commands

```bash
make api              # dev server (uvicorn --reload)
make api-test         # pytest
make api-test-cov     # pytest + coverage >= 90%
make api-lint         # ruff check
make api-typecheck    # mypy src/
make api-fmt          # ruff format
make worker           # taskiq worker (async debrief extraction)
make api-migrate      # alembic upgrade head
make api-migration msg="description"  # new alembic migration

make web              # player web app dev server (packages/web/app)
make backoffice       # backoffice dev server (packages/web/backoffice)
make web-install      # install the whole web workspace (shared + app + backoffice)
make web-test         # vitest (player app)
make web-build        # production build (player app)

make mobile           # Flutter app (packages/mobile)
make mobile-test      # flutter test

make quality-api            # full API quality gate (lint + format + mypy + bandit + typos + pytest >= 90%)
make quality-web            # ALL web gates (shared + app + backoffice)
make quality-web-shared     # shared lib only
make quality-web-app        # player app only
make quality-web-backoffice # backoffice only
make quality-mobile         # Flutter gate
make quality                # ALL quality gates (pre-commit + api + web + mobile)
```

## Architecture — Layer Discipline (strict)

```text
API v1 Routers -> Core Services -> Infrastructure Repositories -> DB Models
```

| Layer | Path | Responsibility |
| ------- | ------ | --------------- |
| Router | `api/v1/{domain}.py` | Parse request, validate, call service, return response. NO business logic. |
| Service | `core/{domain}/service.py` | Business logic, orchestration. Calls repos only. NO direct DB access. |
| Schemas | `core/{domain}/schemas.py` | Pydantic v2 request/response models |
| Repository | `infrastructure/db/repositories/{domain}.py` | All DB access via SQLAlchemy async. No business logic. |
| Model | `infrastructure/db/models/{domain}.py` | ORM definition. No methods with business logic. |

## Domain Rules

1. **LLM outputs are untrusted** — always validate via anti-hallucination checks (token overlap threshold)
2. **One active mission per user** — enforce at service level before creating new missions
3. **Captures are immutable after processing** — status flows: `pending -> processing -> done | failed`
4. **Loadout suggestions expire** — auto-ignored after `loadout_auto_ignore_hours` (24h default)
5. **Missions auto-clamp** — ended after `mission_auto_clamp_hours` (24h default)
6. **UUID v4 with public_id** — internal `id` is auto-increment, `public_id` is UUID exposed to API
7. **All timestamps UTC** in DB; frontend displays in user timezone
8. **English everywhere** — code, comments, UI, variable names all in English

## Hard Rules

1. **No business logic in routers** — routers parse and delegate to service, nothing more
2. **No DB access in services** — services call repositories; never import Session in a service
3. **Coverage >= 90%** for API package — enforced by `make quality-api`
4. **Async everywhere** — `async def` for all route handlers and service methods doing I/O
5. **No `Any` in Pydantic schemas** — use explicit types
6. **Files <= 300 lines** — enforced by `make api-file-sizes`
7. **Conventional commits** — `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`
8. **Never commit secrets** — `.env` files are gitignored, use `settings.py` with defaults
9. **Never use `git add .`** — add specific files to avoid accidentally staging secrets
10. **Never use `--no-verify`** — pre-commit hooks exist for a reason
11. **Always use `poetry run`** — all Python commands must run inside the poetry virtualenv (e.g. `poetry run python -m pytest`, `poetry run detect-secrets`)

## LLM Integration Pattern

```text
Jinja2 template (prompts/*.j2)
    -> LLMClient.generate(prompt, model)
    -> Parse JSON response
    -> Anti-hallucination validation (token overlap)
    -> Persist result
```

- **Fast model** (`gemma3:4b`): captures, quick extraction
- **Smart model** (`gemma3:12b`): briefings, loadout picks
- **Vision model** (`qwen3-vl:4b`): photo captures
- **Dummy provider**: testing (returns canned responses)

## Background Jobs (Taskiq + Redis)

| Task | Trigger | Purpose |
| ------ | --------- | --------- |
| `extract_debrief_state_task` | Mission debrief submitted | Extract emotional state from debrief text via LLM |
| `mission_auto_clamp` | Periodic | End missions older than 24h |
| `loadout_auto_ignore` | Periodic | Ignore stale loadout suggestions |

Retry policy: exponential backoff (2s -> 4s -> 8s), max 3 retries.

## Quality Gates

Run `make quality` before shipping. It runs:

- Pre-commit hooks (detect-secrets, ruff, biome)
- API: ruff lint + format + mypy + bandit + typos + file sizes + pytest >= 90%
- Web: biome + tsc + vitest + vite build
- Code duplication: jscpd <= 5%

## Reference Documents

- [PRODUCT.md](./PRODUCT.md) — product spec, flows, features
- [ARCHITECTURE.md](./ARCHITECTURE.md) — technical decisions, schema, module structure
- [ROADMAP.md](./ROADMAP.md) — epics, milestones, status
- [docs/API.md](./docs/API.md) — endpoint reference
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) — deployment guides
- [docs/OLLAMA.md](./docs/OLLAMA.md) — LLM configuration
