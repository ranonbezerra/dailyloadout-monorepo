---
name: dailyloadout-conventions
autoload: true
description: Core conventions for all DailyLoadout development. Auto-loaded for every task.
---

# DailyLoadout Conventions

## FastAPI Backend (`packages/api/`)

### Layer Structure (strict — no exceptions)
```
API v1 Routers -> Core Services -> Infrastructure Repositories -> DB Models
```

| Layer | Responsibility | Imports from |
|-------|---------------|--------------|
| Router (`api/v1/`) | Parse request, validate, call service, return response | Deps, Schemas |
| Service (`core/{domain}/service.py`) | Business logic, orchestration | Repository |
| Repository (`infrastructure/db/repositories/`) | DB access (SQLAlchemy async) | Model |
| Model (`infrastructure/db/models/`) | ORM definition (no methods with logic) | Nothing |

### File Naming
- `api/v1/{domain}.py` — plural domain in URL prefix (`/api/v1/missions`)
- `core/{domain}/service.py` — singular domain directory
- `core/{domain}/schemas.py` — Pydantic v2 schemas
- `deps/{domain}.py` — dependency injection
- `infrastructure/db/models/{domain}.py` — singular domain
- `infrastructure/db/repositories/{domain}.py` — singular domain
- `tests/test_{domain}.py` — test file per domain

### Pydantic v2 Conventions
- Always use `model_config = ConfigDict(from_attributes=True)` for response schemas
- Never use `Any` type — be explicit
- Use `UUID` from `uuid` module for public_id fields
- Date/time fields: `datetime` from stdlib

### SQLAlchemy 2.x Conventions
- All models inherit from `Base` + mixins (`TimestampMixin`, `PublicIDMixin`)
- PK: auto-increment `id` (internal only)
- Public ID: `public_id: Mapped[str]` UUID v4, exposed to API
- Timestamps: `created_at`, `updated_at` as `TIMESTAMPTZ` with `server_default=func.now()`
- Relationships: use `relationship()` with `lazy="selectin"` or explicit `joinedload()`
- Always filter by user to prevent cross-user data access

### Error Handling
```python
from fastapi import HTTPException

# Standard pattern — use HTTPException directly
raise HTTPException(status_code=404, detail="Mission not found")
raise HTTPException(status_code=409, detail="Active mission already exists")

# Common status codes:
# 404: entity not found
# 409: conflict (duplicate, active mission exists)
# 422: validation error (invalid input)
# 401: unauthorized
# 403: forbidden (wrong user)
```

### API Versioning
- All endpoints under `/api/v1/` prefix
- Breaking changes require new version (`/api/v2/`)
- Non-breaking additions (new fields) are fine in same version

### LLM Integration
- Prompts in `prompts/*.j2` (Jinja2 templates)
- LLM client abstraction in `infrastructure/llm/base.py`
- Providers: `ollama.py` (production), `dummy.py` (testing)
- Always validate LLM output with anti-hallucination checks
- Never trust raw LLM output — parse, validate, then persist

## React Web Dashboard (`packages/web/`)

### Architecture
- **Route definitions** in `App.tsx` (React Router v7)
- **Server state** via TanStack Query (never raw useEffect + fetch)
- **UI primitives** from Mantine v7 (never build from scratch)
- **API calls** in `lib/` directory

### Naming Conventions
- Components: `PascalCase` (`MissionBriefingModal.tsx`)
- Hooks: `camelCase` with `use` prefix (`useMission.ts`)
- Types: `PascalCase` (`Mission`, `LibraryEntry`)
- API functions: `camelCase` (`fetchMissions`, `createMission`)
- Query keys: domain-based arrays (`["missions", "list"]`)

### API Response Transformation
Backend uses snake_case, frontend uses camelCase. Transform at the API layer using the `snakeToCamel` utility.

### TanStack Query Pattern
```typescript
const QUERY_KEY = ["domain"] as const;

export function useDomain() {
  return useQuery({ queryKey: QUERY_KEY, queryFn: fetchDomain });
}

export function useCreateDomain() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createDomain,
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}
```

## Universal Rules

- **public_id (UUID v4)** for all entity IDs exposed to API
- **UTC timestamps** in DB; display timezone conversion in frontend only
- **LLM outputs are untrusted** — validate before persisting
- **One active mission per user** — enforced at service level
- **Captures are immutable** after processing — status: `pending -> processing -> done | failed`
- **Code in English** — variable names, comments, types, UI text all English
- **Conventional Commits** — `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`
- **Coverage >= 90%** for API package
- **Files <= 300 lines** for API Python files

## Prohibited Patterns

### WRONG: Business logic in router
```python
# BAD — router should only parse and delegate
@router.post("/missions/")
async def create_mission(body: CreateMission, session: AsyncSession = Depends(...)):
    existing = await session.execute(select(Mission).where(...))  # WRONG!
```

### WRONG: Direct DB access in service
```python
# BAD — service must use repository
class MissionService:
    async def create(self, session: AsyncSession):
        stmt = select(Mission).where(...)  # WRONG! Use repository
```

### WRONG: Trusting LLM output without validation
```python
# BAD — LLM can hallucinate game names
response = await llm.generate(prompt)
games = json.loads(response)  # WRONG! Must validate against library
```

### WRONG: Missing user isolation
```python
# BAD — allows accessing another user's data
async def get_mission(self, public_id: str) -> Mission:
    return await self.repo.get_by_public_id(public_id)  # WRONG! Must filter by user_id
```
