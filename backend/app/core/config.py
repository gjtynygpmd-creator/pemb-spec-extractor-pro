
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket: str = "pemb-project-files"
    s3_region: str = "auto"
    cors_origins: str = "http://localhost:8888"
    max_file_size_gb: int = 20
    upload_expiration_seconds: int = 3600
    openai_api_key: str = ""

    # --- v1.9.x vision extraction (provider-agnostic) ---
    # Provider for the vision path: "openai" (default, matches existing setup) or "anthropic".
    vision_provider: str = "openai"
    vision_extraction_enabled: bool = True
    # openai_api_key is defined above; anthropic_api_key below is only needed when
    # vision_provider is "anthropic".
    anthropic_api_key: str = ""
    vision_model_openai: str = "gpt-4o"
    vision_model_anthropic: str = "claude-opus-4-8"
    vision_dpi: int = 200

    # Page routing thresholds. A page goes to the fast regex path only when its
    # text layer is both long enough and label-dense enough to parse reliably.
    # Otherwise it is routed to the vision path (drawings, scanned, image-only).
    text_layer_min_chars: int = 200
    text_layer_min_labels: int = 3

    # --- v1.9.2 stability / memory safety ---
    # Cap the rendered image size so large-format sheets (ARCH-D/E) don't blow up
    # worker memory. The longest edge is limited to vision_max_edge_px regardless
    # of vision_dpi, which is what previously risked an out-of-memory kill.
    vision_max_edge_px: int = 2200
    # Hard ceiling on vision calls per job, to bound cost and runtime on very large
    # scanned sets. Pages beyond this are flagged for review instead of sent.
    vision_max_pages_per_job: int = 300
    # Truncate pathological pages so regex/memory can't spike on a single sheet.
    page_text_char_cap: int = 100000
    # A job whose heartbeat (updated_at) is older than this is considered stuck,
    # e.g. because the worker was OOM-killed mid-page. The poll loop recovers it.
    worker_stale_seconds: int = 600
    # Maximum times a job is retried after a stuck/crash recovery before it is
    # marked failed with a clear message.
    worker_max_attempts: int = 3
    # Network timeout (seconds) for a single vision API call, with retries disabled,
    # so a hung provider request fails fast instead of stalling the worker.
    vision_timeout_seconds: int = 60
    # Hard wall-clock guard (seconds) around a single page's render+vision step. A hang
    # (as opposed to an exception) is not caught by try/except; this bounds it so the
    # job moves on and the page is flagged for review.
    page_timeout_seconds: int = 120

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
