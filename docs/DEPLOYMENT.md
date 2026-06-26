# DailyLoadout — Deployment Guide

This document covers deploying DailyLoadout beyond local development. All examples assume you have a working local setup first (`make up && make api`).

---

## Prerequisites

- PostgreSQL 18+ with `citext`, `pg_trgm`, `pgcrypto` extensions
- Redis 7+
- Ollama (local or remote) with at least one model pulled
- Python 3.14+ (API)
- Bun (web static build)

---

## 1. VPS (Hetzner, DigitalOcean, Linode)

The simplest production setup: everything on one machine.

### 1.1 Provision

A 4 vCPU / 8 GB RAM VPS handles the full stack including Ollama with `gemma3:4b`. For `gemma3:12b`, use 16 GB RAM or offload Ollama to a GPU instance.

### 1.2 Setup

```bash
# Clone and configure
git clone https://github.com/ranonbezerra/dailyloadout-monorepo.git
cd dailyloadout-monorepo
cp .env.example .env
```

Edit `.env` with production values:

```env
APP_ENV=production
SECRET_KEY=<generate-a-64-char-random-string>

# Strong, unique secrets — REQUIRED. Compose refuses to start without these.
# Never reuse the dev default "dailyloadout".
POSTGRES_PASSWORD=<generate-a-32-char-random-string>
REDIS_PASSWORD=<generate-a-32-char-random-string>

DATABASE_URL=postgresql+asyncpg://dailyloadout:<POSTGRES_PASSWORD>@postgres:5432/dailyloadout
# Redis requires auth now; include the password in the URL.
REDIS_URL=redis://:<REDIS_PASSWORD>@redis:6379/0
CORS_ORIGINS=["https://your-domain.com"]

# Cookies served over HTTPS only. Required in production. If web and API are on
# different domains you'll use AUTH_COOKIE_SAMESITE=none, which forces Secure.
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax

# Single-user mode (recommended for personal use)
SINGLE_USER_MODE=true
SINGLE_USER_EMAIL=you@example.com
```

> Note on hostnames: when the API/worker run as Docker Compose services they
> reach Postgres and Redis by service name (`postgres:5432`, `redis:6379`).
> If you run the API on the host during local dev, use the loopback ports
> published by `docker-compose.override.yml` (`localhost:5433`, `localhost:6380`).

### 1.3 Compose file layout & workflow

The stack is split into a safe-by-default base plus environment overlays:

| File | Loaded when | What it adds |
| --- | --- | --- |
| `docker-compose.yml` | always | All services on the internal network. **No published backing-service ports.** Redis auth + required `${POSTGRES_PASSWORD}`/`${REDIS_PASSWORD}`. |
| `docker-compose.override.yml` | auto, on plain `docker compose up` | Publishes Postgres/Redis on **loopback only** (`127.0.0.1:5433`, `127.0.0.1:6380`) for local DB tools. |
| `docker-compose.prod.yml` | only with explicit `-f` | Resource limits, `cap_drop: [ALL]`, `no-new-privileges`, read-only rootfs, non-root `appuser`, restart policy. **No published ports.** |

```bash
# Local development — base + auto-loaded override (loopback DB access):
docker compose up -d            # or: make up
ollama serve &                  # or install as a systemd service
ollama pull gemma3:4b
ollama pull gemma3:12b

# Production — explicit -f means the dev override is NOT applied:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

> **Network isolation (critical).** The base file publishes NO ports for
> Postgres, Redis, or SearXNG — they are reachable only over the internal
> compose network. This matters because **Docker bypasses the host firewall**:
> Docker inserts its own iptables rules (the `DOCKER` chain) evaluated before
> UFW, so a `5433:5432` mapping on `0.0.0.0` is reachable from the public
> internet even with `ufw deny 5433` active. The dev override publishes only on
> `127.0.0.1`, so it is harmless even if accidentally applied elsewhere. The
> prod overlay publishes nothing. **Never bind a backing service to `0.0.0.0`.**
> For production DB access, see §1.8 (Emergency production database access).

### 1.4 Run the API

```bash
cd packages/api
poetry install --without dev
poetry run alembic upgrade head
poetry run uvicorn src.dailyloadout.main:app --host 0.0.0.0 --port 8100 --workers 2 \
    --proxy-headers --forwarded-allow-ips "127.0.0.1"
```

> `--proxy-headers --forwarded-allow-ips <trusted-proxy>` is required when the
> API sits behind Caddy. Without it, uvicorn ignores `X-Forwarded-For` and the
> auth rate limiter sees every request as coming from the proxy's IP — one
> shared bucket for all clients, so the limiter is useless. Set
> `--forwarded-allow-ips` to ONLY the proxy address: `127.0.0.1` when Caddy runs
> on the same host as a host-process API, or the docker bridge gateway
> (`172.17.0.1`, the Dockerfile default via `FORWARDED_ALLOW_IPS`) when the API
> runs in a container. Never use `*` in production — it lets any client spoof
> its source IP.

For the Taskiq background worker (async debrief extraction):

```bash
poetry run taskiq worker dailyloadout.infrastructure.tasks.debrief_extraction:broker
```

### 1.5 Build and serve the web dashboard

```bash
cd packages/web
bun install
VITE_API_URL=https://your-domain.com/api bun run build
```

Serve `dist/` with nginx, Caddy, or any static file server.

### 1.6 Reverse proxy (Caddy example)

**Single-edge model.** Caddy is the *only* internet-facing process. It
terminates TLS, applies security headers and a request body cap, then proxies
`/api/*` to the API on loopback and serves the web build for everything else.
Everything behind it — Postgres, Redis, SearXNG, the API, the worker — listens
only on the internal network / loopback (see §1.3).

```caddyfile
your-domain.com {
    # --- Security headers (apply to every response) ---
    header {
        # HSTS: 2 years, include subdomains. Browsers force HTTPS afterward.
        Strict-Transport-Security "max-age=63072000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        # CSP tuned for the web app: self-hosted JS, Google Fonts for styles,
        # IGDB cover images. No inline/eval JS, no plugins, no framing.
        Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: https://images.igdb.com; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        # Don't advertise the server software.
        -Server
    }

    # Cap request bodies at the edge (uploads/JSON). Stops oversized-payload
    # abuse before it reaches the API.
    request_body {
        max_size 25MB
    }

    handle /api/* {
        # API listens on loopback only; Caddy is the trusted proxy that sets
        # X-Forwarded-For (uvicorn runs with --forwarded-allow-ips 127.0.0.1).
        reverse_proxy localhost:8100
    }
    handle {
        root * /path/to/packages/web/dist
        file_server
        try_files {path} /index.html
    }
}
```

> If you add CDN/asset domains or analytics later, widen the CSP `connect-src` /
> `img-src` / `script-src` deliberately — keep `object-src 'none'`,
> `base-uri 'none'`, and `frame-ancestors 'none'`.

### 1.7 systemd services

Create service files for persistent operation:

```ini
# /etc/systemd/system/dailyloadout-api.service
[Unit]
Description=DailyLoadout API
After=network.target postgresql.service redis.service

[Service]
User=dailyloadout
WorkingDirectory=/opt/dailyloadout/packages/api
ExecStart=/opt/dailyloadout/packages/api/.venv/bin/uvicorn src.dailyloadout.main:app --host 0.0.0.0 --port 8100 --workers 2 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=always
EnvironmentFile=/opt/dailyloadout/.env

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/dailyloadout-worker.service
[Unit]
Description=DailyLoadout Taskiq Worker
After=network.target redis.service

[Service]
User=dailyloadout
WorkingDirectory=/opt/dailyloadout/packages/api
ExecStart=/opt/dailyloadout/packages/api/.venv/bin/taskiq worker dailyloadout.infrastructure.tasks.debrief_extraction:broker
Restart=always
EnvironmentFile=/opt/dailyloadout/.env

[Install]
WantedBy=multi-user.target
```

### 1.8 Emergency production database access

**Principle: the database port is never bound to `0.0.0.0`.** In production
Postgres is published on the VPS **loopback only** (`127.0.0.1:5432`) — not on
the network — and Redis/SearXNG publish nothing. All access is gated by **SSH
key auth** to the VPS: a network scan finds no DB port, and the loopback bind is
reachable only through an SSH tunnel.

**Primary path — exec into the running container (zero network exposure):**

```bash
ssh you@vps
# Interactive psql shell:
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    exec postgres psql -U dailyloadout dailyloadout

# Backup (run on the VPS, stream to a local file):
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    exec -T postgres pg_dump -U dailyloadout dailyloadout > backup.sql
```

This never opens a port at all — `exec` runs the client inside the container
over Docker's local socket.

**GUI path — DataGrip/DBeaver over SSH (desktop client):**

The prod overlay binds Postgres to the VPS loopback (`127.0.0.1:5432`), so a
desktop client reaches it through your GUI's built-in SSH tunnel — no extra
steps, no toggling. In DataGrip (DBeaver / TablePlus are equivalent):

- **SSH/SSL tab** → enable *Use SSH tunnel* → Host = the VPS, Port = 22, key auth.
- **General tab** → Host = `127.0.0.1`, Port = `5432`, with your DB user/password/db.

DataGrip SSHes into the VPS and connects to its loopback Postgres over the
encrypted tunnel — the port is never on the network. (Plain-CLI alternative:
`ssh -L 5432:127.0.0.1:5432 you@vps`, then point any tool at `localhost:5432`.)

Three independent gates protect the DB: your **SSH key**, the **loopback-only**
bind (no network reachability), and the **Postgres password**.

> Do NOT "temporarily" publish the DB on `0.0.0.0` for a GUI tool. Remember
> Docker's iptables rules bypass UFW, so that exposes the database to the whole
> internet. SSH tunneling to a loopback-bound port is the only sanctioned GUI
> path.

---

## 2. Fly.io

### 2.1 Services

| Service | Fly config |
| --- | --- |
| API | `fly launch` in `packages/api/` with a `Dockerfile` |
| Postgres | Fly Postgres (`fly postgres create`) |
| Redis | Fly Redis (`fly redis create`) or Upstash |
| Ollama | Separate Fly machine with GPU (or external) |
| Web | Static site on Fly or Cloudflare Pages |

### 2.2 Environment

Set secrets via `fly secrets set`:

```bash
fly secrets set SECRET_KEY="..."
fly secrets set DATABASE_URL="postgres://..."
fly secrets set REDIS_URL="redis://..."
fly secrets set OLLAMA_BASE_URL="http://ollama-app.internal:11434"
fly secrets set SINGLE_USER_MODE=true
fly secrets set SINGLE_USER_EMAIL="you@example.com"
```

### 2.3 Dockerfile for the API

```dockerfile
FROM python:3.14-slim

WORKDIR /app
RUN pip install poetry
COPY packages/api/pyproject.toml packages/api/poetry.lock ./
RUN poetry install --without dev --no-root

COPY packages/api/src ./src
COPY packages/api/alembic ./alembic
COPY packages/api/alembic.ini ./

RUN poetry install --without dev

EXPOSE 8100
# Behind Fly's proxy: trust forwarded headers from Fly's edge. Fly forwards from
# the platform; "*" is acceptable only because Fly Machines are not directly
# reachable except through Fly's proxy. On a self-managed VPS prefer a specific
# proxy IP instead (see §1.4).
CMD ["poetry", "run", "uvicorn", "src.dailyloadout.main:app", "--host", "0.0.0.0", "--port", "8100", "--proxy-headers", "--forwarded-allow-ips", "*"]
```

### 2.4 Migrations

Run before deploy or as a release command:

```bash
fly ssh console -C "poetry run alembic upgrade head"
```

---

## 3. Railway

Railway auto-detects Python projects. Point the service root to `packages/api/`.

### 3.1 Services

- **API**: Python service from `packages/api/`
- **Postgres**: Railway managed PostgreSQL
- **Redis**: Railway managed Redis
- **Web**: Static deploy from `packages/web/dist/`
- **Ollama**: External (Railway doesn't offer GPU instances)

### 3.2 Environment variables

Set via the Railway dashboard or CLI. Same variables as the VPS setup. Railway provides `DATABASE_URL` and `REDIS_URL` automatically for managed services.

### 3.3 Build command

```bash
poetry install --without dev && poetry run alembic upgrade head
```

### 3.4 Start command

```bash
poetry run uvicorn src.dailyloadout.main:app --host 0.0.0.0 --port ${PORT:-8100}
```

---

## 4. Ollama deployment considerations

Ollama can run on the same machine as the API or on a dedicated GPU instance.

| Setup | Pros | Cons |
| --- | --- | --- |
| Same machine (CPU) | Simple, no network latency | Slow inference on `gemma3:12b` |
| Same machine (GPU) | Fast inference, simple | Requires GPU VPS (expensive) |
| Separate GPU instance | API scales independently | Network latency, more infra |
| External API (Bedrock) | No self-hosted GPU needed | Cloud cost, not fully local |

Set `OLLAMA_BASE_URL` to point at the Ollama instance. For a separate machine, ensure the port is accessible (default `11434`).

See [OLLAMA.md](./OLLAMA.md) for model selection and hardware requirements.

---

## 5. Storage

| Provider | Config | Use case |
| --- | --- | --- |
| `local_fs` | `STORAGE_PROVIDER=local_fs` | Single machine, default |
| `s3` | `STORAGE_PROVIDER=s3` + S3 env vars | Multi-instance, durable |

For S3-compatible storage (Cloudflare R2, Backblaze B2), set:

```env
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=dailyloadout-uploads
AWS_S3_ENDPOINT_URL=https://...  # for non-AWS providers
```

Audio and image files are temporary -- they're deleted after capture processing completes.

---

## 6. Security checklist

Secrets (all must-set in production — compose refuses to start without the DB
and Redis passwords):

- [ ] Set a strong `SECRET_KEY` (at least 64 random characters)
- [ ] Set a strong `POSTGRES_PASSWORD` — **must-set**, never the dev default `dailyloadout`
- [ ] Set a strong `REDIS_PASSWORD` — **must-set**; reflect it in `REDIS_URL` (`redis://:<pw>@redis:6379/0`)
- [ ] **Rotate any secret that has ever lived on a workstation** (committed `.env`, shell history, screenshare). Treat workstation-exposed secrets as compromised.

Edge & transport:

- [ ] Use HTTPS (Caddy auto-TLS, or Fly/Railway built-in)
- [ ] Caddy emits security headers (HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP) and `request_body { max_size 25MB }` — see §1.6
- [ ] Set `AUTH_COOKIE_SECURE=true` (cookies HTTPS-only). If web/API are cross-domain you'll need `AUTH_COOKIE_SAMESITE=none`, **which requires Secure** — browsers reject `SameSite=None` cookies without it.
- [ ] Set `CORS_ORIGINS` to your actual domain(s)
- [ ] Run uvicorn with `--proxy-headers --forwarded-allow-ips <trusted-proxy>` so client IPs (and the auth rate limiter) survive the proxy hop — see §1.4

Network isolation:

- [ ] **No published backing-service ports.** Postgres/Redis/SearXNG bound to the internal compose network only (not `0.0.0.0`). Remember Docker's iptables rules bypass UFW — an exposed port is internet-reachable regardless of the host firewall. See §1.3.
- [ ] SearXNG `limiter: true` (set in `infra/searxng/settings.yml`)
- [ ] Keep Ollama behind a firewall (not exposed to the internet)

Operations:

- [ ] Enable `SINGLE_USER_MODE` if self-hosting for personal use
- [ ] Deploy with the prod overlay (`-f docker-compose.yml -f docker-compose.prod.yml`): containers run non-root (`USER appuser`) with `cap_drop: [ALL]`, `no-new-privileges`, read-only rootfs, and resource limits — see `docker-compose.prod.yml`
- [ ] Run database backups (`pg_dump` cron or managed provider snapshots) — see §1.8 for the SSH-exec backup command
