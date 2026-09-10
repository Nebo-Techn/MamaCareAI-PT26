"""
Pipeline configuration.

Every tunable value in the pipeline lives here and comes from the environment.
Nothing is hardcoded in a stage.

WHY THIS IS STRICT
A threshold buried in a stage (`if confidence < 0.9:`) cannot be tuned without
a deploy, cannot differ between dev and prod, and cannot be found by someone
who does not already know it exists. Every number below started life as a
magic number in someone's first draft.

The adapter-selection fields (`translation_engine`, `object_store_backend`, ...)
are what make PDF section 6's open questions answerable LATER. Build against
the ports, run the free stack locally, flip a config value when the volume and
budget questions are settled.

TODO (junior dev): add the corresponding keys to `backend/config/.env.example`
whenever you add a field here. A setting that only exists in code is a setting
the next person deploys without.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    """Environment-driven pipeline settings.

    Loaded once at startup and injected. Never call this constructor inside a
    stage — a stage that reads config at call time cannot be tested with
    different settings without patching the environment.
    """

    model_config = SettingsConfigDict(
        env_file="config/.env", env_prefix="PIPELINE_", extra="ignore"
    )

    # --- Adapter selection: the free MVP stack by default --------------------
    # docs/ARCHITECTURE.md: no budget provisioned. Defaults must run on a
    # laptop with no cloud account. Production overrides them via env vars.
    queue_backend: str = "memory"  # memory | sqs | kafka
    object_store_backend: str = "filesystem"  # filesystem | s3
    search_backend: str = "sqlite"  # sqlite | opensearch
    database_url: str = "sqlite:///./data/pipeline.db"

    # --- Language detection (PDF 3.3) ----------------------------------------
    language_detector: str = "fasttext"  # fasttext | cloud
    # Below this, a human confirms the language instead of the model guessing.
    # Tune from real data: an always-empty confirmation queue means it is too
    # low to be doing anything.
    language_confidence_threshold: float = 0.90
    target_language: str = "sw"

    # --- Translation (PDF 3.4, PDF section 6) --------------------------------
    translation_engine: str = "nllb"  # nllb | google | aws | azure
    # Max characters per chunk sent to the MT engine. Provider-dependent —
    # check the actual API limit before changing this.
    translation_max_chunk_chars: int = 4000
    translation_batch_size: int = 16

    # --- Retries & backoff (PDF section 4, Orchestration) --------------------
    max_attempts: int = 5
    backoff_base_seconds: float = 2.0
    backoff_cap_seconds: float = 600.0

    # --- Ingestion limits ----------------------------------------------------
    # Guards against one enormous file taking down a worker.
    fetch_timeout_seconds: float = 30.0
    fetch_max_bytes: int = 100 * 1024 * 1024  # 100 MB
    respect_robots_txt: bool = True  # do not set this to False.
    user_agent: str = "MamaCareAI-DataPipeline/0.1 (+contact: nebotechtz@gmail.com)"

    # --- Extraction quality gate ---------------------------------------------
    # Below this, extraction is treated as failed rather than passing junk on.
    min_extracted_chars: int = 200

    # --- Storage paths (filesystem backend) ----------------------------------
    object_store_path: str = "./data/02_raw"

    # --- Compliance (PDF section 4) ------------------------------------------
    compliance_strict: bool = True  # unknown licence -> block. Keep True.
    allowed_licenses: str = "public-domain,CC0,CC-BY-4.0,permission-granted"

    # --- Observability -------------------------------------------------------
    metrics_enabled: bool = True
    log_level: str = "INFO"

    def allowed_license_set(self) -> frozenset[str]:
        """Parse the comma-separated licence allowlist.

        Splits on commas, strips whitespace, drops empties. Env vars are
        strings; parse them in ONE place rather than at every use site.
        """
        return frozenset(
            part.strip() for part in self.allowed_licenses.split(",") if part.strip()
        )
