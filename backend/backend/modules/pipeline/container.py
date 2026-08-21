"""
Composition root — the ONE place that knows which adapter fills which port.

THIS IS THE MOST IMPORTANT FILE FOR UNDERSTANDING THE DESIGN.

Every other file in this package depends on abstractions. This file, and only
this file, imports concrete classes (S3ObjectStore, NLLBTranslator, ...) and
wires them together. Dependency Inversion has to be resolved SOMEWHERE — the
discipline is keeping that somewhere to a single file at the edge of the
system, instead of scattering `S3Client()` calls through twelve modules.

WHAT THIS BUYS THE TEAM, CONCRETELY
  - Run the whole pipeline locally, free, with zero cloud accounts:
    filesystem + SQLite + in-memory queue.
  - Run it in production on S3 + Postgres + SQS by changing environment
    variables — no code change in any stage.
  - Run it in tests with fakes, by calling `build_test_container()`.
  Same stages in all three. That is the payoff for the ports/adapters layout.

RULE: no business logic here. If you are writing an `if` about a resource's
status in this file, it belongs in a stage.

TODO (junior dev): implement the factory functions below. Keep each one boring —
read a config value, construct one adapter, return it. Boring is correct here.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import PipelineSettings
from .ports.deduplicator import Deduplicator
from .ports.job_queue import JobQueue
from .ports.language_detector import LanguageDetector
from .ports.object_store import ObjectStore
from .ports.repositories import (
    DocumentRepository,
    ResourceRepository,
    ReviewRepository,
    VersionRepository,
)
from .ports.search_index import SearchIndex
from .ports.translator import Translator
from .registry import ExtractorRegistry, FetcherRegistry
from .stages.base import Stage


@dataclass(slots=True)
class Container:
    """Every wired dependency the pipeline needs. Built once at startup."""

    settings: PipelineSettings
    queue: JobQueue
    object_store: ObjectStore
    search: SearchIndex
    deduplicator: Deduplicator
    detector: LanguageDetector
    translator: Translator
    fetchers: FetcherRegistry
    extractors: ExtractorRegistry
    resources: ResourceRepository
    documents: DocumentRepository
    versions: VersionRepository
    reviews: ReviewRepository

    def stage(self, name: str) -> Stage:
        """Build the stage with the given name, fully wired.

        TODO: map "ingest" -> IngestStage(...), etc. Raise a clear error for an
        unknown name, listing the valid ones — a typo in a worker command
        should fail in one second with a useful message, not start a worker
        that silently consumes nothing.
        """
        raise NotImplementedError


# --- Factories: config value in, adapter out ---------------------------------
#
# Each factory is the ONLY place its adapter is constructed. When someone asks
# "where does the pipeline decide to use S3?", the answer is one function.


def build_queue(settings: PipelineSettings) -> JobQueue:
    """memory | sqs | kafka.

    TODO: default "memory" must work with zero setup — a trainee cloning this
    repo should be able to run the pipeline end to end on their laptop within
    ten minutes. If the free path needs an AWS account, we have failed the
    "no budget provisioned" constraint in docs/ARCHITECTURE.md.
    """
    raise NotImplementedError


def build_object_store(settings: PipelineSettings) -> ObjectStore:
    """filesystem | s3."""
    raise NotImplementedError


def build_search_index(settings: PipelineSettings) -> SearchIndex:
    """sqlite (FTS5) | opensearch."""
    raise NotImplementedError


def build_translator(settings: PipelineSettings) -> Translator:
    """nllb | google | aws | azure — PDF section 6's open question, as config.

    TODO: fail fast and loudly at STARTUP if the selected engine's credentials
    or model files are missing. Discovering a missing API key on the first
    translation job, after the queue has already accepted 500 documents, is a
    much worse afternoon than discovering it at boot.
    """
    raise NotImplementedError


def build_detector(settings: PipelineSettings) -> LanguageDetector:
    """fasttext | cloud.

    TODO: load the fastText lid.176 model ONCE here and share it. Loading a
    model per job is the classic way to make a cheap stage expensive.
    """
    raise NotImplementedError


def build_fetchers(settings: PipelineSettings) -> FetcherRegistry:
    """Register the web, video, and PDF fetchers.

    TODO: this is the ONE place a new source type gets plugged in. If adding a
    source type requires editing anything in `stages/`, the Open/Closed
    Principle has been broken — fix the design, not the symptom.
    """
    raise NotImplementedError


def build_extractors(settings: PipelineSettings) -> ExtractorRegistry:
    """Register extractors WITH PRIORITIES — this is the fallback chain.

    TODO, and the priorities matter:
        html            priority 100
        pdf_text_layer  priority 100
        pdf_ocr         priority  50   <- only when the text layer declines
        video_captions  priority 100
        video_asr       priority  50   <- only when there are no captions;
                                          the most expensive step in the pipeline
    Get these numbers wrong and you will run OCR on every text-layer PDF and
    wonder why the bill and the latency are both terrible.
    """
    raise NotImplementedError


def build_container(settings: PipelineSettings | None = None) -> Container:
    """Build the production container from environment settings.

    TODO: call each factory once and return a Container. Called by
    `worker.py`, `cli.py`, and the FastAPI lifespan hook in `backend/main.py`.
    Build it ONCE per process — rebuilding per request reloads models and
    reopens connection pools.
    """
    raise NotImplementedError


def build_test_container(**overrides: object) -> Container:
    """Build a container of in-memory fakes for tests.

    TODO: wire the fakes from `tests/pipeline/fakes.py` — in-memory
    repositories, a list-backed queue, a dict-backed object store, a translator
    that returns "[sw] " + text, a detector that returns a fixed language.
    Let `**overrides` replace any single dependency, so a test can inject one
    failing adapter and leave the rest real.

    THIS FUNCTION IS WHY THE WHOLE PORTS LAYER EXISTS. Every stage test should
    be able to start with one line:

        container = build_test_container()

    and run the full pipeline with no network, no database, no API keys, and no
    model downloads — in milliseconds. If a test needs credentials, something
    has been wired wrongly; find the concrete import that leaked into a stage.
    """
    raise NotImplementedError
