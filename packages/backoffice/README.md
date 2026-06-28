# DailyLoadout · Backoffice

The internal **admin** app — a standalone frontend, separate from the player app
(`packages/web`). Both talk to the same API (`packages/api`): the backoffice uses
the admin-only `/internal/v1` surface (plus `/v1/auth` for login), the player app
uses `/v1`.

It is deliberately its own package so admin code never ships to players and the
two products can deploy and evolve independently.

## Develop

```bash
bun install
bun run dev        # http://localhost:5174 (player app runs on 5173)
bun run test       # vitest (≥90% line coverage)
bun run lint       # biome
bun run build      # tsc + vite build
```

Point it at an API with `VITE_API_URL` (default `http://localhost:8100`).

## Access

Sign in with an account that holds a backoffice admin grant
(`packages/api/scripts/grant_admin.py`). Non-admins get a 403 "no access" screen.
Single-user mode is rejected at the API boundary.
