from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ── Core ─────────────────────────────────────────────────────────────
    app_env: str = "development"
    secret_key: str = "change-me-in-prod"
    cors_origins: list[str] = [
        "http://localhost:3200",
        "http://localhost:5173",
    ]
    # Host allowlist (TrustedHostMiddleware). ["*"]=dev; set API domain(s) in prod.
    trusted_hosts: list[str] = ["*"]

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://slate:slate@localhost:5433/slate"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6380/0"
    # Best-effort caching (IGDB lookups, etc.); off => NullCache (Epic 17).
    cache_enabled: bool = True
    # Per-user stats cached for a short time, bust on play_session start/end/wrap_up (Epic 18).
    stats_cache_ttl_seconds: int = 300
    # Deep recaps are content-addressed on the session context (Epic 18). 7d.
    recap_cache_ttl_seconds: int = 7 * 24 * 3600
    research_cache_ttl_seconds: int = 6 * 3600  # web-research network-hop cache
    llm_cache_ttl_seconds: int = 24 * 3600  # idempotent LLM completions, by content
    reference_cache_ttl_seconds: int = 3600  # genre list etc. — tiny, hot

    # ── Single-user mode ─────────────────────────────────────────────────
    single_user_mode: bool = False
    single_user_email: str = ""

    # ── LLM ──────────────────────────────────────────────────────────────
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_fast_model: str = "gemma3:4b"
    ollama_smart_model: str = "gemma3:12b"
    ollama_vision_model: str = "qwen3-vl:4b"
    llm_timeout_seconds: int = 60
    ollama_warmup_models: list[str] = []  # background-preload on startup; empty = off
    ollama_warmup_keep_alive: str = "30m"  # how long warmed models stay resident ('-1' = pinned)
    ollama_max_concurrency: int = 2  # cap concurrent host-Ollama calls (avoids GPU thrash)

    # ── Embeddings / RAG over PlaySession history (Epic 24) ───────────────
    embedding_provider: str = "dummy"  # ollama | dummy
    ollama_embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768  # must match the model; a change = migration + re-embed
    recap_retrieval: str = "recent"  # recent | semantic — the A/B grounding source

    # ── Agent / Deep Research Recap (Epic 10) ─────────────────────────
    agent_provider: str = "dummy"  # langgraph | dummy
    research_provider: str = "dummy"  # searxng | dummy
    searxng_base_url: str = "http://localhost:8888"
    deep_recap_deadline_seconds: int = 60
    deep_recap_max_refines: int = 2
    deep_recap_max_results: int = 6
    deep_recap_scrape_top_n: int = 2  # scrape top-N result URLs into full text (0 = snippets only)
    # Overlap floor for the DEEP recap — more tolerant than quick's 0.40 (grounds on
    # research text the verbatim token match can't fully cover).
    deep_recap_overlap_threshold: float = 0.25

    # ── Backlog Concierge (Epic 11) ──────────────────────────────────────
    concierge_provider: str = "dummy"  # langgraph | dummy
    # Tool-calling model — qwen2.5-instruct: fast, coherent tool use.
    ollama_agent_model: str = "qwen2.5:7b-instruct"
    concierge_agent_reasoning: bool = False
    concierge_max_tool_loops: int = 6
    concierge_checkpointer: str = "postgres"  # postgres survives restarts, else memory (Epic 16)
    concierge_write_tools_enabled: bool = True  # write tools drive the pipeline (Epic 12)

    # ── STT ──────────────────────────────────────────────────────────────
    stt_provider: str = "dummy"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # ── OCR / library import (Epic 14) ───────────────────────────────────
    ocr_provider: str = "tesseract"  # tesseract | dummy
    # Low-confidence fallback to the vision model; "none" disables it.
    ocr_fallback_provider: str = "vision"  # vision | none
    # Below this mean line confidence, escalate the image to the vision fallback.
    ocr_confidence_threshold: float = 0.6
    # Fuzzy-match cutoff for accepting an OCR line as a canonical game.
    catalog_match_min_score: float = 0.6
    # Anti-abuse (Block C): distinct owners that promote a private manual row to
    # globally shared/discoverable (spam hidden until enough users own it).
    catalog_share_threshold: int = 5
    # Bulk-import cap (each candidate fans out to an IGDB lookup → DoS guard).
    library_import_max_candidates: int = 40
    # Free-tier abuse/cost guards (per user, per UTC day).
    library_import_images_per_day: int = 10
    library_import_vision_fallbacks_per_day: int = 20
    # Hard cap on files per bulk-import request, checked before any file is read.
    library_import_max_files: int = 20

    # ── Storage ──────────────────────────────────────────────────────────
    storage_provider: str = "local_fs"
    storage_local_path: str = "/var/lib/slate/uploads"
    capture_upload_dir: str = "uploads/captures"

    # ── IGDB (optional) ──────────────────────────────────────────────────
    igdb_client_id: str = ""
    igdb_client_secret: str = ""
    # Cache IGDB search results this long (game metadata is stable). 7 days.
    igdb_cache_ttl_seconds: int = 7 * 24 * 3600

    # ── Social login / OAuth (Auth Code + PKCE) — provider on when client id set ──
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    twitch_oauth_client_id: str = ""
    twitch_oauth_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:8100"
    oauth_web_success_url: str = "http://localhost:5173/oauth/callback"
    oauth_web_error_url: str = "http://localhost:5173/login"
    oauth_state_ttl_seconds: int = 600  # single-use PKCE/state entry in Redis

    # ── Email (optional) ─────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Slate <noreply@slate.local>"

    # ── Registration identity hygiene (anti-abuse) ───────────────────────
    # Disposable blocklist + MX/A DNS probe (FAILS OPEN, prod-only, short budget).
    block_disposable_emails: bool = True
    check_email_mx: bool = True
    email_mx_timeout_seconds: float = 3.0

    # ── Email verification (account integrity) — signed purpose-scoped JWTs ──
    email_verification_ttl_hours: int = 24
    # Public base URL the verification link points at (deep link appends token).
    email_verification_base_url: str = "http://localhost:5173/verify-email"

    # ── Password reset — signed purpose-scoped JWTs, short TTL, bumps tv ──
    password_reset_ttl_hours: int = 1
    password_reset_base_url: str = "http://localhost:5173/reset-password"

    # ── MFA / TOTP (Phase 2) — issuer + short-lived 2-step challenge token ──
    mfa_issuer: str = "Slate"
    mfa_challenge_ttl_minutes: int = 5

    # ── CAPTCHA (Cloudflare Turnstile) ───────────────────────────────────
    # Empty => Turnstile dependency is a no-op; set => register needs a token.
    turnstile_secret: str = ""
    turnstile_verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    # ── Auth ───────────────────────────────────────────────────────
    bcrypt_rounds: int = 12

    # ── Auth refresh cookie (web cookie-mode, X-Auth-Mode: cookie) ───────
    # App uses BODY mode; web only. PROD: secure=True, samesite="none" cross-domain.
    auth_cookie_name: str = "slate_refresh_token"
    # Secure by default; dev may set False for http://localhost (prod refuses False).
    auth_cookie_secure: bool = True
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_path: str = "/v1/auth"
    auth_cookie_domain: str | None = None
    # Grace after rotation: a replay within it is a benign refresh race, not theft.
    auth_refresh_reuse_grace_seconds: int = 10

    # ── Limits ───────────────────────────────────────────────────────────
    capture_max_audio_seconds: int = 60
    capture_max_image_mb: int = 10
    capture_max_audio_mb: int = 5
    capture_max_games_per_shelf: int = 12
    play_session_auto_clamp_hours: int = 24
    pick_auto_ignore_hours: int = 24
    pick_cooldown_hours: int = 12

    # ── Rate limiting (Redis fixed-window, per-user / per-IP) ────────────
    # Master switch (False => rate_limit() is a no-op). Also fails open if Redis is down.
    rate_limit_enabled: bool = True
    # Auth limiters (per client IP) — Redis-backed, shared across workers.
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_minute: int = 5
    # Per-USER limits on expensive (LLM/IGDB/research) routes — tuned for COST.
    rate_limit_concierge_chat_per_minute: int = 6
    rate_limit_play_session_recap_per_minute: int = 4
    rate_limit_pick_create_per_minute: int = 10
    rate_limit_capture_submit_per_minute: int = 15
    rate_limit_library_import_per_minute: int = 5
    rate_limit_candidate_rematch_per_minute: int = 20
    # POST /v1/games (LLM/IGDB resolve) + generous backstops on writes/reads.
    rate_limit_game_create_per_minute: int = 20
    rate_limit_library_write_per_minute: int = 60
    rate_limit_read_per_minute: int = 120

    # ── Cost kill-switch (aggregate $ guard, provider-agnostic) ──────────
    # Spend proxy: 503s over budgets (False => no-op); degrades on Redis error.
    cost_guard_enabled: bool = True
    cost_global_per_minute: int = 120
    cost_global_per_day: int = 5000
    cost_global_per_month: int = 100000
    cost_user_per_day: int = 200
    cost_alert_threshold: float = 0.8
    cost_guard_degraded_fallback_enabled: bool = True
    cost_guard_fallback_workers: int = 1

    # Default per-user middleware limit (backstop for routes lacking a limiter).
    rate_limit_default_per_minute: int = 120

    # Per-user/day outbound-IGDB budget shared by create_game/capture. Fails OPEN.
    igdb_user_budget_per_day: int = 300

    # Concurrent Whisper transcriptions (mirrors ollama) + per-call token cap.
    stt_max_concurrency: int = 2
    llm_max_output_tokens: int = 1024

    # ── Request hardening (DoS / security headers) ───────────────────────
    # Reject requests over this Content-Length with 413 before the body is read.
    max_request_body_bytes: int = 25 * 1024 * 1024
    # HSTS max-age in seconds advertised to browsers (~2 years).
    hsts_max_age_seconds: int = 63072000
    # Disable Scalar /docs + /openapi.json outside dev/test (production lockdown).
    docs_enabled: bool = True
    # Allowlist of hosts an IGDB cover_url may point at (https only); else nulled.
    igdb_cdn_allowed_hosts: list[str] = ["images.igdb.com"]

    # Echo SQL to the logs (debug-only noise) — opt in with DB_ECHO=true.
    db_echo: bool = False

    # ── DB connection pool (sized for a small multi-worker deploy) ───────
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    db_pool_pre_ping: bool = True

    # ── Observability (optional) ─────────────────────────────────────────
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    # LLM/graph tracing (Epic 23): spans per model call + graph node; capture
    # adds redacted prompt/completion previews (off by default — PII).
    tracing_enabled: bool = True
    trace_capture_enabled: bool = False

    @property
    def is_production(self) -> bool:
        """True outside dev/testing. Fail-safe: ``app_env`` is normalised (trim +
        lowercase) and ONLY exact dev/test values relax security — any unknown,
        empty, or typo'd value is treated as production."""
        return self.app_env.strip().lower() not in _DEV_ENVS


_DEV_ENVS = ("development", "testing")


def _validate_production_settings(s: Settings) -> None:
    """Fail fast on insecure production configuration.

    Dev/test (``app_env`` in ``development``/``testing``) may relax these so
    http://localhost keeps working; any other environment is treated as
    production and must be hardened.
    """
    if not s.is_production:
        return

    if s.secret_key == "change-me-in-prod":
        raise RuntimeError(
            "FATAL: secret_key is still the default value. "
            "Set the SECRET_KEY environment variable before running in production."
        )

    if len(s.secret_key) < 32:
        raise RuntimeError(
            "FATAL: secret_key is too short for production (< 32 chars). "
            "Use a high-entropy value (e.g. `secrets.token_urlsafe(48)`)."
        )

    if not s.auth_cookie_secure:
        raise RuntimeError(
            "FATAL: auth_cookie_secure must be True in production. "
            "Refresh-token cookies must only be sent over HTTPS."
        )

    if s.auth_cookie_samesite == "none" and not s.auth_cookie_secure:
        raise RuntimeError("FATAL: auth_cookie_samesite='none' requires auth_cookie_secure=True.")

    if s.single_user_mode:
        raise RuntimeError(
            "FATAL: single_user_mode must be False in production. "
            "It bypasses JWT auth and returns a fixed account for every request."
        )

    if not s.turnstile_secret:
        raise RuntimeError(
            "FATAL: turnstile_secret must be set in production. The registration "
            "CAPTCHA is the primary defence against mass account creation."
        )


settings = Settings()

_validate_production_settings(settings)
