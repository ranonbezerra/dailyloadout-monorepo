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
DATABASE_URL=postgresql+asyncpg://dailyloadout:<password>@localhost:5433/dailyloadout
REDIS_URL=redis://localhost:6380/0
CORS_ORIGINS=["https://your-domain.com"]

# Single-user mode (recommended for personal use)
SINGLE_USER_MODE=true
SINGLE_USER_EMAIL=you@example.com
```

### 1.3 Start infrastructure

```bash
make up           # postgres + redis via Docker Compose
ollama serve &    # or install as a systemd service
ollama pull gemma3:4b
ollama pull gemma3:12b
```

### 1.4 Run the API

```bash
cd packages/api
poetry install --without dev
poetry run alembic upgrade head
poetry run uvicorn src.dailyloadout.main:app --host 0.0.0.0 --port 8100 --workers 2
```

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

```caddyfile
your-domain.com {
    handle /api/* {
        reverse_proxy localhost:8100
    }
    handle {
        root * /path/to/packages/web/dist
        file_server
        try_files {path} /index.html
    }
}
```

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
ExecStart=/opt/dailyloadout/packages/api/.venv/bin/uvicorn src.dailyloadout.main:app --host 0.0.0.0 --port 8100 --workers 2
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
CMD ["poetry", "run", "uvicorn", "src.dailyloadout.main:app", "--host", "0.0.0.0", "--port", "8100"]
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

- [ ] Set a strong `SECRET_KEY` (at least 64 random characters)
- [ ] Use HTTPS (Caddy auto-TLS, or Fly/Railway built-in)
- [ ] Set `CORS_ORIGINS` to your actual domain(s)
- [ ] Use a strong `POSTGRES_PASSWORD`
- [ ] Enable `SINGLE_USER_MODE` if self-hosting for personal use
- [ ] Keep Ollama behind a firewall (not exposed to the internet)
- [ ] Run database backups (`pg_dump` cron or managed provider snapshots)
