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

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://dailyloadout:dailyloadout@localhost:5433/dailyloadout"
    )

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6380/0"
    # Best-effort caching (IGDB lookups, etc.); off => NullCache (Epic 17).
    cache_enabled: bool = True
    # Per-user stats are recomputed on every dashboard load; cache them briefly
    # and bust on mission start/end/debrief (ROADMAP Epic 18). 5 minutes.
    stats_cache_ttl_seconds: int = 300
    # Deep briefings (~4 LLM calls + web research) are content-addressed on the
    # session context, so a new debrief yields a fresh key. Long TTL. 7 days.
    briefing_cache_ttl_seconds: int = 7 * 24 * 3600
    # Web-research queries repeat across briefings; cache the network hop. 6h.
    research_cache_ttl_seconds: int = 6 * 3600
    # Idempotent LLM completions, de-duped by content. 1 day.
    llm_cache_ttl_seconds: int = 24 * 3600
    # Reference data (genre list, etc.) — tiny, hot, rarely changes. 1 hour.
    reference_cache_ttl_seconds: int = 3600

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
    # Preload these Ollama models in the background on startup so the first real
    # request isn't a slow cold-load (the concierge agent especially). Empty =
    # disabled. Local example: '["qwen2.5:7b-instruct"]'. Only runs when
    # LLM_PROVIDER=ollama.
    ollama_warmup_models: list[str] = []
    # How long warmed models stay resident after idle. Default frees the RAM
    # after 30 min; set '-1' to pin them loaded indefinitely (always fast, but
    # holds the memory).
    ollama_warmup_keep_alive: str = "30m"
    # Process-wide ceiling on concurrent model calls to the host Ollama server
    # (per worker process). A burst of concierge/briefing requests would
    # otherwise oversubscribe the GPU/CPU and stall every in-flight call; this
    # bounds the queue depth so the model serves a few requests fast rather than
    # thrashing all of them. Holds only around the model HTTP call.
    ollama_max_concurrency: int = 2

    # ── Agent / Deep Research Briefing (Epic 10) ─────────────────────────
    agent_provider: str = "dummy"  # langgraph | dummy
    research_provider: str = "dummy"  # searxng | dummy
    searxng_base_url: str = "http://localhost:8888"
    deep_briefing_deadline_seconds: int = 60
    deep_briefing_max_refines: int = 2
    deep_briefing_max_results: int = 6
    # Scrape the top-N result URLs into full text for richer synthesis grounding.
    # 0 = snippets only (cheaper/faster, less specific). Trade-off: scraping adds
    # latency + tokens and enlarges the spoiler surface the filter must catch.
    deep_briefing_scrape_top_n: int = 2

    # ── Backlog Concierge (Epic 11) ──────────────────────────────────────
    concierge_provider: str = "dummy"  # langgraph | dummy
    # Tool-calling model — Gemma is weak at function-calling. qwen2.5-instruct does
    # fast, coherent tool use with no <think> overhead (qwen3 reasoning is slow;
    # qwen3 without reasoning is incoherent on multi-step grounded tasks).
    ollama_agent_model: str = "qwen2.5:7b-instruct"
    # Qwen3 is a reasoning model: its <think> chains add huge latency to every
    # ReAct step. Disable for fast tool-calling; enable only if answer quality
    # demands deliberation.
    concierge_agent_reasoning: bool = False
    concierge_max_tool_loops: int = 6
    # Where conversation threads are checkpointed (ROADMAP Epic 16). 'postgres'
    # persists them to the existing DB so chats survive restarts; 'memory' keeps
    # them in-process (lost on restart). Falls back to memory if Postgres init
    # fails. Only used by the langgraph provider.
    concierge_checkpointer: str = "postgres"
    # Give the Concierge write tools (start_mission, generate_briefing,
    # submit_retroactive_debrief, set_status) so it can drive the mission
    # pipeline, not just recommend (ROADMAP Epic 12).
    concierge_write_tools_enabled: bool = True

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
    # Bulk-import path replaces the single-shelf cap of 12. Lowered from 200 as
    # a DoS mitigation: each candidate fans out to an IGDB lookup. The full
    # async/Taskiq move is a separate follow-up.
    library_import_max_candidates: int = 40
    # Free-tier abuse/cost guards (per user, per UTC day).
    library_import_images_per_day: int = 10
    library_import_vision_fallbacks_per_day: int = 20
    # Hard cap on files accepted in a single bulk-import request, checked BEFORE
    # any file is read into memory (DoS backstop on top of the per-day quota).
    library_import_max_files: int = 20

    # ── Storage ──────────────────────────────────────────────────────────
    storage_provider: str = "local_fs"
    storage_local_path: str = "/var/lib/dailyloadout/uploads"
    capture_upload_dir: str = "uploads/captures"

    # ── IGDB (optional) ──────────────────────────────────────────────────
    igdb_client_id: str = ""
    igdb_client_secret: str = ""
    # Cache IGDB search results this long (game metadata is stable). 7 days.
    igdb_cache_ttl_seconds: int = 7 * 24 * 3600

    # ── OAuth Google (optional) ──────────────────────────────────────────
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    # ── Email (optional) ─────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "DailyLoadout <noreply@dailyloadout.local>"

    # ── Auth ───────────────────────────────────────────────────────
    bcrypt_rounds: int = 12

    # ── Auth refresh cookie (web cookie-mode, X-Auth-Mode: cookie) ───────
    # The Flutter app uses BODY mode (no cookie); these only affect web.
    # Dev-friendly defaults: Secure off + SameSite lax so http://localhost
    # works. PRODUCTION: set auth_cookie_secure=True, and if web/api live on
    # different domains set auth_cookie_samesite="none" (which requires Secure).
    auth_cookie_name: str = "dl_refresh_token"
    # Secure by default; dev/test may override to False so http://localhost works.
    # Production startup refuses to boot with this False (see guard below).
    auth_cookie_secure: bool = True
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_path: str = "/v1/auth"
    auth_cookie_domain: str | None = None

    # ── Limits ───────────────────────────────────────────────────────────
    capture_max_audio_seconds: int = 60
    capture_max_image_mb: int = 10
    capture_max_audio_mb: int = 5
    capture_max_games_per_shelf: int = 12
    mission_auto_clamp_hours: int = 24
    loadout_auto_ignore_hours: int = 24
    loadout_cooldown_hours: int = 12

    # ── Rate limiting (Redis fixed-window, per-user / per-IP) ────────────
    # Master switch. False => the rate_limit() dependency is a no-op (used in
    # tests and any deploy that wants it off). The limiter ALSO fails open if
    # Redis is unreachable, so the API never hard-fails on a limiter error.
    rate_limit_enabled: bool = True
    # Auth limiters (per client IP) — migrated from in-memory pyrate_limiter to
    # Redis so the window is shared across worker processes.
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_minute: int = 5
    # Per-USER limits on the expensive (LLM / IGDB / research) routes. Tuned
    # conservatively for COST (each call is a paid Vertex/Bedrock request, and
    # the concierge fans out to several model calls per turn), not just abuse.
    rate_limit_concierge_chat_per_minute: int = 6
    rate_limit_mission_briefing_per_minute: int = 4
    rate_limit_loadout_create_per_minute: int = 10
    rate_limit_capture_submit_per_minute: int = 15
    rate_limit_library_import_per_minute: int = 5

    # ── Request hardening (DoS / security headers) ───────────────────────
    # Coarse backstop: reject any request whose Content-Length exceeds this cap
    # with HTTP 413 before the body is read. ~25 MB covers the largest legit
    # upload (multi-image library import) with headroom.
    max_request_body_bytes: int = 25 * 1024 * 1024
    # HSTS max-age in seconds advertised to browsers (~2 years).
    hsts_max_age_seconds: int = 63072000
    # Disable Scalar /docs + /openapi.json outside dev/test (production lockdown).
    docs_enabled: bool = True
    # Allowlist of hosts an IGDB cover_url may point at (https only). Anything
    # else is rejected/nulled to keep poisoned URLs out of LLM prompts + the UI.
    igdb_cdn_allowed_hosts: list[str] = ["images.igdb.com"]

    # ── DB connection pool (sized for a small multi-worker deploy) ───────
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    db_pool_pre_ping: bool = True

    # ── Observability (optional) ─────────────────────────────────────────
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""


_DEV_ENVS = ("development", "testing")


def _validate_production_settings(s: Settings) -> None:
    """Fail fast on insecure production configuration.

    Dev/test (``app_env`` in ``development``/``testing``) may relax these so
    http://localhost keeps working; any other environment is treated as
    production and must be hardened.
    """
    if s.app_env in _DEV_ENVS:
        return

    if s.secret_key == "change-me-in-prod":
        raise RuntimeError(
            "FATAL: secret_key is still the default value. "
            "Set the SECRET_KEY environment variable before running in production."
        )

    if not s.auth_cookie_secure:
        raise RuntimeError(
            "FATAL: auth_cookie_secure must be True in production. "
            "Refresh-token cookies must only be sent over HTTPS."
        )

    if s.auth_cookie_samesite == "none" and not s.auth_cookie_secure:
        raise RuntimeError("FATAL: auth_cookie_samesite='none' requires auth_cookie_secure=True.")


settings = Settings()

_validate_production_settings(settings)
