# Slate — Pre-Launch Runbook

The ordered checklist to take Slate from "merged on `main`" to "live on a
VPS". This is the **what to do, in order**; [DEPLOYMENT.md](./DEPLOYMENT.md) is
the **how** for each piece (linked per step). Security/anti-abuse hardening is
already shipped — this runbook is the operational wiring that activates it.

> Convention: `api.example.com` = your API domain, `app.example.com` = your web
> domain. Use one domain with `/api/*` routing if you prefer (see DEPLOYMENT §1.6).

---

## Phase 0 — Register external accounts (collect credentials first)

You can't fill the `.env` files without these. Do them up front.

- [ ] **Cloudflare Turnstile** — dash → Turnstile → add a site → copy the
      **Site Key** (web) and **Secret Key** (API). *Required in prod — the API
      refuses to boot without `TURNSTILE_SECRET`.*
- [ ] **IGDB / Twitch app** — <https://dev.twitch.tv/console> → register an
      application → copy **Client ID / Secret** (these are `IGDB_CLIENT_ID/SECRET`).
- [ ] **Google OAuth** — Google Cloud Console → OAuth consent screen + Credentials
      → Web client. Authorized redirect URI:
      `https://api.example.com/v1/auth/oauth/google/callback`. Scopes: `openid email profile`.
- [ ] **Twitch OAuth (user login)** — a Twitch app (can reuse the IGDB one or a
      separate one). OAuth Redirect URL:
      `https://api.example.com/v1/auth/oauth/twitch/callback`. Copy Client ID/Secret.
- [ ] **SMTP provider** — (Postmark / SES / Mailgun / etc.) for verification emails.
      Copy host / port / user / password.
- [ ] **Off-host backup storage** — an S3-compatible bucket (Cloudflare R2 /
      Backblaze B2 / AWS S3) + credentials for `rclone`.
- [ ] **DNS** — point `api.example.com` (and `app.example.com`) A/AAAA records at
      the VPS IP. (Set TTL low now to ease changes.)
- [ ] **CD deploy key** — generate a dedicated SSH key for the GitHub Actions
      deploy; add the public key (forced-command) to the VPS, the private key as
      the `VPS_SSH_KEY` repo secret. See DEPLOYMENT §1.10. *(deploys are
      per-surface: API/infra is migration-gated via `deploy-api.yml`; web/app/
      backoffice ship on their own.)*

---

## Phase 1 — Provision the VPS

See DEPLOYMENT §1.1.

- [ ] 4 vCPU / 8 GB (16 GB if running `gemma3:12b` on-box) — Hetzner/DO/Linode.
- [ ] Create a non-root sudo user; **SSH key auth only**, disable password login.
- [ ] `ufw default deny incoming` + allow `22, 80, 443`. ⚠ **Docker bypasses UFW**
      — never publish a DB/Redis port on `0.0.0.0` (DEPLOYMENT §1.3).
- [ ] Install Docker + compose plugin; install Ollama on the host (`ollama serve`)
      and `ollama pull` your `OLLAMA_FAST_MODEL` / `OLLAMA_SMART_MODEL` /
      `OLLAMA_VISION_MODEL` / `OLLAMA_AGENT_MODEL`.
- [ ] `git clone` the repo to `/opt/slate` (the systemd units assume this path).

---

## Phase 2 — Configure the three `.env` files

Generate strong secrets: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.

### 2a. Root `.env` (compose / infra) — `cp .env.example .env`
- [ ] `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` — **required** (compose `${VAR:?}`).
- [ ] `REDIS_PASSWORD` — **required**.
- [ ] `SEARXNG_SECRET` — **required** (compose refuses to boot without it).

### 2b. API `.env` — `cp packages/api/.env.example packages/api/.env`
The API **refuses to boot in production** unless these are right (fail-fast guards):
- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` — **≥ 32 chars**, not the default.
- [ ] `AUTH_COOKIE_SECURE=true` (and `AUTH_COOKIE_SAMESITE=none` only if web/API are
      on different domains — that forces Secure, which you have).
- [ ] `SINGLE_USER_MODE=false`
- [ ] `TURNSTILE_SECRET=<from Phase 0>`

Required for the app to work in prod:
- [ ] `DATABASE_URL` / `REDIS_URL` — real creds (Redis URL includes the password).
- [ ] `CORS_ORIGINS=["https://app.example.com"]` · `TRUSTED_HOSTS=["api.example.com"]`
- [ ] Providers off `dummy`: `AGENT_PROVIDER=langgraph`, `RESEARCH_PROVIDER=searxng`,
      `CONCIERGE_PROVIDER=langgraph`, `STT_PROVIDER=whisper_local`.
- [ ] `IGDB_CLIENT_ID/SECRET`, `GOOGLE_OAUTH_*`, `TWITCH_OAUTH_*`.
- [ ] `OAUTH_REDIRECT_BASE_URL=https://api.example.com` ·
      `OAUTH_WEB_SUCCESS_URL=https://app.example.com/oauth/callback` ·
      `OAUTH_WEB_ERROR_URL=https://app.example.com/login`
- [ ] `SMTP_*` + `EMAIL_VERIFICATION_BASE_URL=https://app.example.com/verify-email`
- [ ] `COST_GUARD_FALLBACK_WORKERS=<your uvicorn --workers count>` (e.g. 2).

### 2c. Web build env — `packages/web/.env`
- [ ] `VITE_API_URL=https://api.example.com`
- [ ] `VITE_TURNSTILE_SITE_KEY=<from Phase 0>`
- [ ] `VITE_OAUTH_PROVIDERS=google,twitch`
- [ ] `VITE_ENABLE_CONCIERGE=true` (if you want the concierge live).

---

## Phase 3 — Bring up data + run migrations

See DEPLOYMENT §1.3–1.4.

- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
      (Postgres/Redis/SearXNG/worker — hardened, no published ports).
- [ ] Run migrations: `cd packages/api && poetry run alembic upgrade head`.
- [ ] (Optional) seed platforms / any reference data your build expects.

---

## Phase 4 — API, worker, web, edge

- [ ] **API** via systemd (DEPLOYMENT §1.7), `--workers N` matching
      `COST_GUARD_FALLBACK_WORKERS`, `--forwarded-allow-ips <Caddy's source IP>`.
      ⚠ A wrong `--forwarded-allow-ips` silently collapses per-IP rate limits.
- [ ] **Taskiq worker** via systemd (wrap-up extraction).
- [ ] **Web**: `cd packages/web && bun install && bun run build`; serve `dist/`.
- [ ] **Caddy** (DEPLOYMENT §1.6) — terminates TLS (auto Let's Encrypt), sets the
      web CSP + body cap, proxies `/api/*` → loopback `:8100`, serves the web build.
      Caddy is the **only** internet-facing process.

---

## Phase 5 — Backups (do NOT skip — single VPS = one disk)

See DEPLOYMENT §1.9.

- [ ] `rclone config` → create the off-host remote.
- [ ] `cp infra/backup/backup.env.example /etc/slate/backup.env` → fill
      `POSTGRES_*`, `RCLONE_REMOTE`; `chmod 600`.
- [ ] Install + enable the timer:
      `cp infra/backup/slate-backup.{service,timer} /etc/systemd/system/`
      → `systemctl daemon-reload && systemctl enable --now slate-backup.timer`.
- [ ] Run it once and confirm it lands off-host (`rclone ls <remote>`).
- [ ] **Restore drill** against a scratch DB (`infra/backup/restore-db.sh`).

---

## Phase 6 — Verify before announcing

- [ ] `curl https://api.example.com/health` → `{"status":"ok"}`.
- [ ] `curl https://api.example.com/openapi.json` → **404** (docs disabled in prod).
- [ ] Response headers include `strict-transport-security`, `content-security-policy`,
      `x-frame-options: DENY` (`curl -I`).
- [ ] Register a test account on the web → **verification email arrives** → verify → log in.
- [ ] **OAuth round-trip**: "Continue with Google" and "with Twitch" → land logged in.
- [ ] Turnstile widget renders on register and blocks a scripted submit.
- [ ] Add a game / generate a recap → works; concierge responds.
- [ ] Confirm **no DB/Redis port** is reachable from outside (`nmap` from off-box).
- [ ] Rate limit: hammer `/v1/auth/login` from one IP → 429 (proves
      `--forwarded-allow-ips` is correct and per-IP isolation works).

---

## Phase 7 — Go live & post-launch

- [ ] Lower DNS TTL already done; flip traffic / announce.
- [ ] **AWS Budgets** equivalent / provider spend cap once you move LLM to a paid
      provider (Epic 14) — until then Ollama is $0.
- [ ] Watch logs for `cost_guard_tripped`, `rate_limit_*`, `catalog_game_promoted`
      (`igdb_corroborated=false` → review/`scripts/demote_game.py`).
- [ ] Keep a ban/incident path handy: `scripts/ban_user.py`, `logout-all`,
      bump `token_version`.
- [ ] Rotate any credential that was ever in a chat/screenshot before launch.

---

### Deferred / known low-severity (safe to launch without)
Existence-neutral register (the 409 oracle, gated by CAPTCHA+rate-limit); SearXNG
DNS-rebinding TOCTOU hardening; `python-jose`→PyJWT (usage already safe); base-image
digest pinning; full-disk encryption (LUKS at provision time, if data sensitivity warrants).
