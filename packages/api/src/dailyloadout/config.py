from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ── Core ─────────────────────────────────────────────────────────────
    app_env: str = "development"
    secret_key: str = "change-me-in-prod"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://dailyloadout:dailyloadout@localhost:5433/dailyloadout"
    )

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6380/0"

    # ── Single-user mode ─────────────────────────────────────────────────
    single_user_mode: bool = False
    single_user_email: str = ""

    # ── LLM ──────────────────────────────────────────────────────────────
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_fast_model: str = "gemma3:4b"
    ollama_smart_model: str = "gemma3:12b"
    llm_timeout_seconds: int = 60

    # ── STT ──────────────────────────────────────────────────────────────
    stt_provider: str = "whisper_local"
    whisper_model: str = "base"

    # ── Storage ──────────────────────────────────────────────────────────
    storage_provider: str = "local_fs"
    storage_local_path: str = "/var/lib/dailyloadout/uploads"

    # ── IGDB (optional) ──────────────────────────────────────────────────
    igdb_client_id: str = ""
    igdb_client_secret: str = ""

    # ── OAuth Google (optional) ──────────────────────────────────────────
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    # ── Email (optional) ─────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "DailyLoadout <noreply@dailyloadout.local>"

    # ── Limits ───────────────────────────────────────────────────────────
    capture_max_audio_seconds: int = 60
    capture_max_image_mb: int = 10
    capture_max_games_per_shelf: int = 12
    mission_auto_clamp_hours: int = 8

    # ── Observability (optional) ─────────────────────────────────────────
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""


settings = Settings()
