from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / "config" / ".env"

ENVIRONMENTS = frozenset({"development", "test", "staging", "production"})
PRODUCTION_ENVIRONMENTS = frozenset({"staging", "production"})
QUEUE_BACKENDS = frozenset({"memory", "sqs"})
OBJECT_STORE_BACKENDS = frozenset({"filesystem", "s3"})
SEARCH_BACKENDS = frozenset({"sqlite", "opensearch"})
LANGUAGE_DETECTORS = frozenset({"fasttext"})
TRANSLATION_ENGINES = frozenset(
    {"passthrough", "nllb", "gemini", "google", "aws", "azure"}
)
CLOUD_TRANSLATION_ENGINES = frozenset({"gemini", "google", "aws", "azure"})
DEV_ONLY_TRANSLATION_ENGINES = frozenset({"passthrough"})
LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})

QUEUE_STAGES = (
    "ingest",
    "extract",
    "detect_language",
    "translate",
    "store",
    "review",
    "publish",
)

_LANGUAGE_CODE = re.compile(r"^[a-z]{2,3}$")


def _csv_set(raw: str) -> frozenset[str]:
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_prefix="PIPELINE_",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = "development"
    queue_backend: str = "memory"
    object_store_backend: str = "filesystem"
    search_backend: str = "sqlite"
    database_url: str = Field(default="sqlite:///./data/pipeline.db", repr=False)
    allowed_origins: str = ""
    aws_region: str | None = None
    sqs_ingest_queue_url: str | None = None
    sqs_extract_queue_url: str | None = None
    sqs_detect_language_queue_url: str | None = None
    sqs_translate_queue_url: str | None = None
    sqs_store_queue_url: str | None = None
    sqs_review_queue_url: str | None = None
    sqs_publish_queue_url: str | None = None
    sqs_dead_letter_url: str | None = None

    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_prefix: str = ""
    opensearch_hosts: str = ""
    opensearch_index: str = "mamacare-resources"
    opensearch_username: str | None = None
    opensearch_password: str | None = Field(default=None, repr=False)

    language_detector: str = "fasttext"
    fasttext_model_path: str = "./models/lid.176.bin"
    language_confidence_threshold: float = 0.90
    target_language: str = "sw"
    translate_source_languages: str = "en"
    direct_review_languages: str = "sw"
    translation_engine: str = "nllb"
    translation_max_chunk_chars: int = 4000
    translation_batch_size: int = 16
    translation_api_key: str | None = Field(
        default=None,
        repr=False,
        validation_alias=AliasChoices(
            "GEMINI_API_KEY", "PIPELINE_TRANSLATION_API_KEY", "translation_api_key"
        ),
    )
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 60.0

    max_attempts: int = 5
    backoff_base_seconds: float = 2.0
    backoff_cap_seconds: float = 600.0

    fetch_timeout_seconds: float = 30.0
    fetch_max_bytes: int = 100 * 1024 * 1024
    respect_robots_txt: bool = True
    user_agent: str = "MamaCareAI-DataPipeline/0.1 (+contact: nebotechtz@gmail.com)"

    min_extracted_chars: int = 200
    object_store_path: str = "./data/02_raw"
    compliance_strict: bool = True
    allowed_licenses: str = "public-domain,CC0,CC-BY-4.0,permission-granted"
    metrics_enabled: bool = True
    log_level: str = "INFO"

    @field_validator(
        "environment",
        "queue_backend",
        "object_store_backend",
        "search_backend",
        "language_detector",
        "translation_engine",
        "target_language",
        "translate_source_languages",
        "direct_review_languages",
        mode="before",
    )
    @classmethod
    def _normalize_lower(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_upper(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_settings(self) -> PipelineSettings:
        errors: list[str] = []
        errors.extend(self._check_choices())
        errors.extend(self._check_ranges())
        errors.extend(self._check_language_policy())
        errors.extend(self._check_adapter_requirements())
        if self.is_production:
            errors.extend(self._check_production())
        if errors:
            bullet_list = "\n  - ".join(errors)
            raise ValueError(
                f"Invalid pipeline configuration "
                f"(PIPELINE_ENVIRONMENT={self.environment!r}):\n  - {bullet_list}"
            )
        return self

    def _check_choices(self) -> list[str]:
        errors: list[str] = []
        choices = (
            ("PIPELINE_ENVIRONMENT", self.environment, ENVIRONMENTS),
            ("PIPELINE_QUEUE_BACKEND", self.queue_backend, QUEUE_BACKENDS),
            (
                "PIPELINE_OBJECT_STORE_BACKEND",
                self.object_store_backend,
                OBJECT_STORE_BACKENDS,
            ),
            ("PIPELINE_SEARCH_BACKEND", self.search_backend, SEARCH_BACKENDS),
            ("PIPELINE_LANGUAGE_DETECTOR", self.language_detector, LANGUAGE_DETECTORS),
            (
                "PIPELINE_TRANSLATION_ENGINE",
                self.translation_engine,
                TRANSLATION_ENGINES,
            ),
            ("PIPELINE_LOG_LEVEL", self.log_level, LOG_LEVELS),
        )
        for env_name, value, allowed in choices:
            if value not in allowed:
                errors.append(
                    f"{env_name}={value!r} is not supported; "
                    f"expected one of: {', '.join(sorted(allowed))}"
                )
        return errors

    def _check_ranges(self) -> list[str]:
        errors: list[str] = []
        if not 0.0 < self.language_confidence_threshold <= 1.0:
            errors.append(
                "PIPELINE_LANGUAGE_CONFIDENCE_THRESHOLD must be in (0, 1]"
            )
        positive = (
            ("PIPELINE_TRANSLATION_MAX_CHUNK_CHARS", self.translation_max_chunk_chars),
            ("PIPELINE_TRANSLATION_BATCH_SIZE", self.translation_batch_size),
            ("PIPELINE_GEMINI_TIMEOUT_SECONDS", self.gemini_timeout_seconds),
            ("PIPELINE_MAX_ATTEMPTS", self.max_attempts),
            ("PIPELINE_BACKOFF_BASE_SECONDS", self.backoff_base_seconds),
            ("PIPELINE_BACKOFF_CAP_SECONDS", self.backoff_cap_seconds),
            ("PIPELINE_FETCH_TIMEOUT_SECONDS", self.fetch_timeout_seconds),
            ("PIPELINE_FETCH_MAX_BYTES", self.fetch_max_bytes),
        )
        for env_name, value in positive:
            if value <= 0:
                errors.append(f"{env_name} must be greater than 0 (got {value})")
        if self.min_extracted_chars < 0:
            errors.append("PIPELINE_MIN_EXTRACTED_CHARS must not be negative")
        if self.backoff_cap_seconds < self.backoff_base_seconds:
            errors.append(
                "PIPELINE_BACKOFF_CAP_SECONDS must be >= PIPELINE_BACKOFF_BASE_SECONDS"
            )
        if _blank(self.database_url):
            errors.append("PIPELINE_DATABASE_URL must be set")
        if _blank(self.user_agent):
            errors.append("PIPELINE_USER_AGENT must be set")
        return errors

    def _check_language_policy(self) -> list[str]:
        errors: list[str] = []
        translate = self.translate_source_language_set()
        direct = self.direct_review_language_set()
        for env_name, codes in (
            ("PIPELINE_TARGET_LANGUAGE", {self.target_language}),
            ("PIPELINE_TRANSLATE_SOURCE_LANGUAGES", translate),
            ("PIPELINE_DIRECT_REVIEW_LANGUAGES", direct),
        ):
            bad = sorted(code for code in codes if not _LANGUAGE_CODE.match(code))
            if bad:
                errors.append(
                    f"{env_name} contains invalid ISO 639 code(s): {', '.join(bad)}"
                )
        if not translate:
            errors.append("PIPELINE_TRANSLATE_SOURCE_LANGUAGES must not be empty")
        if self.target_language not in direct:
            errors.append(
                "PIPELINE_DIRECT_REVIEW_LANGUAGES must include "
                f"PIPELINE_TARGET_LANGUAGE ({self.target_language!r})"
            )
        if self.target_language in translate:
            errors.append(
                "PIPELINE_TRANSLATE_SOURCE_LANGUAGES must not include "
                f"PIPELINE_TARGET_LANGUAGE ({self.target_language!r})"
            )
        overlap = sorted(translate & direct)
        if overlap:
            errors.append(
                "A language cannot be both translated and sent to direct review: "
                f"{', '.join(overlap)}"
            )
        return errors

    def _check_adapter_requirements(self) -> list[str]:
        errors: list[str] = []

        if self.translation_engine in CLOUD_TRANSLATION_ENGINES and _blank(
            self.translation_api_key
        ):
            hint = (
                "GEMINI_API_KEY or PIPELINE_TRANSLATION_API_KEY"
                if self.translation_engine == "gemini"
                else "PIPELINE_TRANSLATION_API_KEY"
            )
            errors.append(
                f"PIPELINE_TRANSLATION_ENGINE={self.translation_engine!r} requires {hint}"
            )
        if self.translation_engine == "aws" and _blank(self.aws_region):
            errors.append("PIPELINE_TRANSLATION_ENGINE='aws' requires PIPELINE_AWS_REGION")
        if self.translation_engine == "gemini" and _blank(self.gemini_model):
            errors.append("PIPELINE_GEMINI_MODEL must be set for gemini translation")

        if self.queue_backend == "sqs":
            if _blank(self.aws_region):
                errors.append("PIPELINE_QUEUE_BACKEND='sqs' requires PIPELINE_AWS_REGION")
            if _blank(self.sqs_dead_letter_url):
                errors.append(
                    "PIPELINE_QUEUE_BACKEND='sqs' requires PIPELINE_SQS_DEAD_LETTER_URL"
                )
            missing = self.missing_sqs_queue_settings()
            if missing:
                errors.append(
                    "PIPELINE_QUEUE_BACKEND='sqs' requires a queue URL per stage; "
                    f"missing: {', '.join(missing)}"
                )

        if self.object_store_backend == "s3" and _blank(self.s3_bucket):
            errors.append("PIPELINE_OBJECT_STORE_BACKEND='s3' requires PIPELINE_S3_BUCKET")
        if self.object_store_backend == "filesystem" and _blank(self.object_store_path):
            errors.append(
                "PIPELINE_OBJECT_STORE_BACKEND='filesystem' requires "
                "PIPELINE_OBJECT_STORE_PATH"
            )

        if self.search_backend == "opensearch" and not self.opensearch_host_list():
            errors.append(
                "PIPELINE_SEARCH_BACKEND='opensearch' requires PIPELINE_OPENSEARCH_HOSTS"
            )
        if self.search_backend == "sqlite" and not self.database_url.startswith(
            "sqlite:///"
        ):
            errors.append(
                "PIPELINE_SEARCH_BACKEND='sqlite' derives its file from a "
                "sqlite:/// PIPELINE_DATABASE_URL; use PIPELINE_SEARCH_BACKEND="
                "'opensearch' with a non-SQLite database"
            )

        if self.language_detector == "fasttext" and _blank(self.fasttext_model_path):
            errors.append(
                "PIPELINE_LANGUAGE_DETECTOR='fasttext' requires "
                "PIPELINE_FASTTEXT_MODEL_PATH"
            )

        for origin in self.allowed_origin_list():
            if origin == "*":
                continue
            parts = urlsplit(origin)
            if parts.scheme not in {"http", "https"} or not parts.netloc or (
                parts.path not in {"", "/"}
            ) or parts.query or parts.fragment:
                errors.append(
                    f"PIPELINE_ALLOWED_ORIGINS entry {origin!r} must be a bare "
                    "origin like https://app.example.org"
                )
        return errors

    def _check_production(self) -> list[str]:
        errors: list[str] = []
        env = self.environment

        if self.queue_backend == "memory":
            errors.append(
                f"PIPELINE_QUEUE_BACKEND='memory' is development only; "
                f"{env} needs a durable queue (sqs)"
            )
        if self.object_store_backend == "filesystem":
            errors.append(
                f"PIPELINE_OBJECT_STORE_BACKEND='filesystem' is development only; "
                f"{env} needs persistent object storage (s3)"
            )
        scheme = self.database_url.split("://", 1)[0].lower()
        if not scheme.startswith("postgresql"):
            errors.append(
                f"PIPELINE_DATABASE_URL must point to PostgreSQL in {env} "
                f"(got scheme {scheme!r})"
            )
        if self.search_backend == "sqlite":
            errors.append(
                f"PIPELINE_SEARCH_BACKEND='sqlite' is development only; "
                f"{env} needs opensearch"
            )
        if self.translation_engine in DEV_ONLY_TRANSLATION_ENGINES:
            errors.append(
                f"PIPELINE_TRANSLATION_ENGINE={self.translation_engine!r} "
                f"is development only"
            )

        origins = self.allowed_origin_list()
        if not origins:
            errors.append(f"PIPELINE_ALLOWED_ORIGINS must be set in {env}")
        if "*" in origins:
            errors.append(f"PIPELINE_ALLOWED_ORIGINS must not contain '*' in {env}")
        if env == "production":
            insecure = sorted(o for o in origins if o.startswith("http://"))
            if insecure:
                errors.append(
                    "PIPELINE_ALLOWED_ORIGINS must use https in production: "
                    f"{', '.join(insecure)}"
                )

        if not self.compliance_strict:
            errors.append(f"PIPELINE_COMPLIANCE_STRICT must be true in {env}")
        if not self.respect_robots_txt:
            errors.append(f"PIPELINE_RESPECT_ROBOTS_TXT must be true in {env}")
        return errors

    @property
    def is_production(self) -> bool:
        return self.environment in PRODUCTION_ENVIRONMENTS

    def allowed_license_set(self) -> frozenset[str]:
        return _csv_set(self.allowed_licenses)

    def allowed_origin_list(self) -> list[str]:
        seen: dict[str, None] = {}
        for part in self.allowed_origins.split(","):
            origin = part.strip().rstrip("/")
            if origin:
                seen.setdefault(origin, None)
        return list(seen)

    def translate_source_language_set(self) -> frozenset[str]:
        return _csv_set(self.translate_source_languages)

    def direct_review_language_set(self) -> frozenset[str]:
        return _csv_set(self.direct_review_languages)

    def sqs_queue_urls(self) -> dict[str, str]:
        urls = {
            stage: getattr(self, f"sqs_{stage}_queue_url") for stage in QUEUE_STAGES
        }
        return {stage: url for stage, url in urls.items() if not _blank(url)}

    def missing_sqs_queue_settings(self) -> list[str]:
        configured = self.sqs_queue_urls()
        return [
            f"PIPELINE_SQS_{stage.upper()}_QUEUE_URL"
            for stage in QUEUE_STAGES
            if stage not in configured
        ]

    def opensearch_host_list(self) -> list[str]:
        return [h.strip() for h in self.opensearch_hosts.split(",") if h.strip()]
