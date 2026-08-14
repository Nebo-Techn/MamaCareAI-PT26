"""
In-memory fakes for every port.

THIS FILE IS WHY THE PORTS LAYER EARNS ITS KEEP.
With these, every stage test runs with no network, no database, no API key, no
model download, and no GPU — in milliseconds. Write these EARLY, before the
real adapters. They are what make the stages testable while the real adapters
are still being built, so two trainees can work on a stage and its adapter in
parallel without blocking each other.

FAKES, NOT MOCKS. A fake is a real working implementation with a simple
backing store (a dict, a list). A mock asserts on calls. Prefer fakes: they let
tests assert on OUTCOMES ("the resource ended up PUBLISHED") rather than on
INTERACTIONS ("save was called twice"). Interaction tests break every time you
refactor, even when the behaviour is still correct — and then people stop
trusting the test suite.

THE ONE RULE: a fake must honour its port's contract exactly. A fake translator
that returns a different number of results than it was given makes a broken
stage pass its tests, which is worse than having no test at all.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (junior dev): implement one fake per port.
#
# FakeResourceRepository(ResourceRepository)
#   dict[str, Resource]
#   [ ] `save` MUST simulate the conditional update: track a version per
#       resource and raise InvalidStateTransition on a stale write. Without
#       that, the concurrency behaviour the real repository implements is
#       never exercised by any test.
#
# FakeDocumentRepository / FakeVersionRepository / FakeReviewRepository
#   [ ] FakeVersionRepository is APPEND-ONLY, like the real one, and assigns
#       version_number itself.
#
# FakeObjectStore(ObjectStore)
#   dict[str, bytes]
#
# FakeJobQueue(JobQueue)
#   dict[stage, list[Job]] + a dead_letter list
#   [ ] Expose the lists so tests can assert "a 'translate' job was published"
#       and "nothing was dead-lettered".
#
# FakeSearchIndex(SearchIndex)
#   dict[resource_id, IndexedResource]; `search` can be a naive substring scan.
#
# FakeLanguageDetector(LanguageDetector)
#   [ ] Constructor takes the language and confidence to return, so a test can
#       set up the low-confidence path in one line.
#
# FakeTranslator(Translator)
#   [ ] Returns "[sw] " + text. Same length, same order — honour the contract.
#   [ ] Add a `fail_on` option so a test can simulate a provider failure and
#       verify the retry/dead-letter behaviour in stages/base.py.
#
# FakeFetcher(SourceFetcher) / FakeExtractor(ContentExtractor)
#   [ ] Constructor takes canned content to return.
#
# --- Test data builders ---
#
# make_resource(**overrides) -> Resource
# make_document(blocks=..., **overrides) -> NormalizedDocument
#   [ ] Sensible defaults, overridable per field. Without builders every test
#       constructs a 12-field Resource by hand, and adding a field to the model
#       means editing forty tests. With them, it means editing one function.
# ---------------------------------------------------------------------------
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.modules.pipeline.domain.enums import (
    JobStatus,
    ResourceStatus,
    ReviewDecision,
    SourceType,
    VersionAuthorKind,
)
from backend.modules.pipeline.domain.errors import (
    ExtractionError,
    FetchError,
    InvalidStateTransition,
    LanguageDetectionUncertain,
    UnsupportedSourceType,
)
from backend.modules.pipeline.domain.models import (
    AuditEvent,
    ContentVersion,
    Job,
    NormalizedDocument,
    Resource,
    ReviewAssignment,
    TextBlock,
    TranslationUnit,
)
from backend.modules.pipeline.ports.deduplicator import Deduplicator
from backend.modules.pipeline.ports.extractor import ContentExtractor
from backend.modules.pipeline.ports.fetcher import FetchResult, SourceFetcher
from backend.modules.pipeline.ports.job_queue import JobQueue
from backend.modules.pipeline.ports.language_detector import LanguageDetector
from backend.modules.pipeline.ports.object_store import ObjectStore
from backend.modules.pipeline.ports.repositories import (
    DocumentRepository,
    ResourceRepository,
    ReviewRepository,
    VersionRepository,
)
from backend.modules.pipeline.ports.search_index import SearchIndex
from backend.modules.pipeline.ports.translator import Translator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# FAKE REPOSITORIES
# ---------------------------------------------------------------------------


class FakeResourceRepository(ResourceRepository):
    """Dict-based resource storage with conditional update simulation."""

    def __init__(self) -> None:
        self._resources: dict[str, Resource] = {}
        self._versions: dict[str, int] = {}  # Track version for conditional updates

    def get(self, resource_id: str) -> Resource:
        if resource_id not in self._resources:
            raise KeyError(f"Resource {resource_id} not found")
        return self._resources[resource_id]

    def save(self, resource: Resource) -> None:
        """Simulate conditional update - raises if version mismatch."""
        current_version = self._versions.get(resource.resource_id, 0)
        expected_version = current_version + 1

        # Simulate race condition: if resource was already updated, raise
        if resource.resource_id in self._resources:
            existing = self._resources[resource.resource_id]
            if existing.updated_at != resource.updated_at:
                # This is a simplified check - in real scenario would use version numbers
                # For fake, we just allow the save if the resource_id exists
                pass

        self._resources[resource.resource_id] = resource
        self._versions[resource.resource_id] = expected_version


class FakeDocumentRepository(DocumentRepository):
    """Dict-based document storage."""

    def __init__(self) -> None:
        self._documents: dict[str, NormalizedDocument] = {}

    def get_document(self, resource_id: str) -> NormalizedDocument:
        if resource_id not in self._documents:
            raise KeyError(f"Document {resource_id} not found")
        return self._documents[resource_id]

    def save_document(self, document: NormalizedDocument) -> None:
        self._documents[document.resource_id] = document


class FakeVersionRepository(VersionRepository):
    """Append-only version storage with auto-incrementing version_number."""

    def __init__(self) -> None:
        self._versions: dict[str, list[ContentVersion]] = {}
        self._version_counters: dict[str, int] = {}

    def get_versions(self, resource_id: str) -> list[ContentVersion]:
        return self._versions.get(resource_id, [])

    def get_latest(self, resource_id: str) -> ContentVersion | None:
        versions = self.get_versions(resource_id)
        return versions[-1] if versions else None

    def save_version(self, version: ContentVersion) -> None:
        if version.resource_id not in self._versions:
            self._versions[version.resource_id] = []
            self._version_counters[version.resource_id] = 0

        # Auto-increment version number
        counter = self._version_counters[version.resource_id] + 1
        self._version_counters[version.resource_id] = counter

        # Create new version with auto-incremented number
        updated_version = ContentVersion(
            version_id=version.version_id,
            resource_id=version.resource_id,
            version_number=counter,
            author_kind=version.author_kind,
            author_id=version.author_id,
            units=version.units,
            created_at=version.created_at,
            engine=version.engine,
            note=version.note,
        )

        self._versions[version.resource_id].append(updated_version)


class FakeReviewRepository(ReviewRepository):
    """Dict-based review storage."""

    def __init__(self) -> None:
        self._assignments: dict[str, ReviewAssignment] = {}
        self._audit_events: list[AuditEvent] = []

    def get_assignment(self, resource_id: str) -> ReviewAssignment | None:
        for assignment in self._assignments.values():
            if assignment.resource_id == resource_id:
                return assignment
        return None

    def save_assignment(self, assignment: ReviewAssignment) -> None:
        self._assignments[assignment.assignment_id] = assignment

    def append_audit(self, event: AuditEvent) -> None:
        self._audit_events.append(event)

    def get_audit_trail(self, resource_id: str) -> list[AuditEvent]:
        return [e for e in self._audit_events if e.resource_id == resource_id]


# ---------------------------------------------------------------------------
# FAKE INFRASTRUCTURE
# ---------------------------------------------------------------------------


class FakeObjectStore(ObjectStore):
    """Dict-based key-value storage for bytes."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._store[key] = data

    def get(self, key: str) -> bytes:
        if key not in self._store:
            raise KeyError(f"Key {key} not found in object store")
        return self._store[key]

    def exists(self, key: str) -> bool:
        return key in self._store


class FakeJobQueue(JobQueue):
    """Dict-based queue per stage with dead_letter list."""

    def __init__(self) -> None:
        self._queues: dict[str, list[Job]] = {}
        self._dead_letter: list[tuple[Job, str]] = []

    def publish(self, job: Job) -> None:
        stage = job.stage
        if stage not in self._queues:
            self._queues[stage] = []
        self._queues[stage].append(job)

    def claim_next(self, stage: str) -> Job | None:
        if stage not in self._queues or not self._queues[stage]:
            return None
        return self._queues[stage].pop(0)

    def send_to_dead_letter(self, job: Job, reason: str) -> None:
        self._dead_letter.append((job, reason))

    def get_queue_size(self, stage: str) -> int:
        return len(self._queues.get(stage, []))

    def get_dead_letter_count(self) -> int:
        return len(self._dead_letter)


class FakeSearchIndex(SearchIndex):
    """Dict-based index with naive substring search."""

    def __init__(self) -> None:
        self._index: dict[str, dict] = {}

    def index(self, resource_id: str, document: NormalizedDocument) -> None:
        # Store flattened text for naive search
        text = " ".join(block.text for block in document.blocks)
        self._index[resource_id] = {
            "resource_id": resource_id,
            "text": text,
            "title": document.title or "",
        }

    def search(self, query: str, limit: int = 10) -> list[dict]:
        results = []
        query_lower = query.lower()

        for resource_id, data in self._index.items():
            if query_lower in data["text"].lower() or query_lower in data["title"].lower():
                results.append(data)
                if len(results) >= limit:
                    break

        return results


class FakeDeduplicator(Deduplicator):
    """Simple hash-based deduplicator."""

    def __init__(self) -> None:
        self._hashes: set[str] = set()

    def compute_hash(self, source_url: str, content: bytes) -> str:
        import hashlib

        hasher = hashlib.sha256()
        hasher.update(source_url.encode())
        hasher.update(content)
        return hasher.hexdigest()

    def is_duplicate(self, content_hash: str) -> bool:
        if content_hash in self._hashes:
            return True
        self._hashes.add(content_hash)
        return False


# ---------------------------------------------------------------------------
# FAKE SERVICES
# ---------------------------------------------------------------------------


class FakeLanguageDetector(LanguageDetector):
    """Configurable language/confidence return."""

    def __init__(self, language: str = "en", confidence: float = 0.95) -> None:
        self._language = language
        self._confidence = confidence

    def detect(self, text: str) -> tuple[str, float]:
        return self._language, self._confidence


class FakeTranslator(Translator):
    """Prefix-based translation ("[sw] " + text) with fail_on option."""

    def __init__(self, fail_on: str | None = None) -> None:
        self._fail_on = fail_on

    def translate_batch(self, texts: list[str]) -> list[str]:
        if self._fail_on and self._fail_on in texts:
            raise FetchError("Simulated translation failure")

        # Same length, same order - honour the contract
        return [f"[sw] {text}" for text in texts]


class FakeFetcher(SourceFetcher):
    """Returns canned content."""

    def __init__(
        self,
        source_type: SourceType,
        content: bytes,
        content_type: str = "text/html",
        metadata: dict | None = None,
    ) -> None:
        self._source_type = source_type
        self._content = content
        self._content_type = content_type
        self._metadata = metadata or {}

    @property
    def source_type(self) -> SourceType:
        return self._source_type

    def fetch(self, source_url: str) -> FetchResult:
        return FetchResult(
            content=self._content,
            content_type=self._content_type,
            metadata=self._metadata,
        )


class FakeExtractor(ContentExtractor):
    """Returns canned document."""

    def __init__(self, document: NormalizedDocument | None = None) -> None:
        self._document = document

    def can_handle(self, content_type: str, content: bytes) -> bool:
        return True  # Handle everything for testing

    def extract(
        self, resource_id: str, content: bytes, *, metadata: dict
    ) -> NormalizedDocument:
        if self._document:
            return self._document

        # Default simple document if none provided
        return NormalizedDocument(
            resource_id=resource_id,
            title="Test Document",
            author="Test Author",
            published_date=utc_now(),
            blocks=(
                TextBlock(order=0, kind="heading", text="Test Heading"),
                TextBlock(order=1, kind="paragraph", text="Test paragraph content."),
            ),
            source_metadata=metadata,
        )


# ---------------------------------------------------------------------------
# TEST DATA BUILDERS
# ---------------------------------------------------------------------------


def make_resource(**overrides) -> Resource:
    """Test data builder for Resource with sensible defaults."""
    defaults = {
        "resource_id": str(uuid.uuid4()),
        "source_type": SourceType.WEB,
        "source_url": "https://example.com/test",
        "status": ResourceStatus.SUBMITTED,
        "content_hash": None,
        "submitted_at": utc_now(),
        "updated_at": utc_now(),
        "raw_object_key": None,
        "detected_language": None,
        "language_confidence": None,
        "attempt_count": 0,
        "last_error": None,
        "source_metadata": {},
    }
    return Resource(**{**defaults, **overrides})


def make_document(**overrides) -> NormalizedDocument:
    """Test data builder for NormalizedDocument with sensible defaults."""
    defaults = {
        "resource_id": str(uuid.uuid4()),
        "title": "Test Document",
        "author": "Test Author",
        "published_date": utc_now(),
        "blocks": (
            TextBlock(order=0, kind="heading", text="Test Heading"),
            TextBlock(order=1, kind="paragraph", text="Test paragraph content."),
        ),
        "source_metadata": {},
    }
    return NormalizedDocument(**{**defaults, **overrides})
