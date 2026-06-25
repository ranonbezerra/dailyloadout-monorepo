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
    # Bulk-import path replaces the single-shelf cap of 12.
    library_import_max_candidates: int = 200
    # Free-tier abuse/cost guards (per user, per UTC day).
    library_import_images_per_day: int = 10
    library_import_vision_fallbacks_per_day: int = 20

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

    # ── Limits ───────────────────────────────────────────────────────────
    capture_max_audio_seconds: int = 60
    capture_max_image_mb: int = 10
    capture_max_games_per_shelf: int = 12
    mission_auto_clamp_hours: int = 24
    loadout_auto_ignore_hours: int = 24
    loadout_cooldown_hours: int = 12

    # ── Observability (optional) ─────────────────────────────────────────
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""


settings = Settings()

if (
    settings.app_env not in ("development", "testing")
    and settings.secret_key == "change-me-in-prod"
):
    raise RuntimeError(
        "FATAL: secret_key is still the default value. "
        "Set the SECRET_KEY environment variable before running in production."
    )
