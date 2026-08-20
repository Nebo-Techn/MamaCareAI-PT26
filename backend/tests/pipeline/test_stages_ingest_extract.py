"""
Tests for the stage template method, plus the ingest and extract stages.

**Owner: Dev A** (see the Sprint 1 split in `docs/PIPELINE_BACKLOG.md`).
Nobody else edits this file during Sprint 1 — that is what keeps four people
working in parallel without a daily merge conflict.

The template-method tests live here because Dev A owns `stages/base.py`. They
are written ONCE and cover behaviour every stage inherits, so the other two
stage test files do not repeat them.

WHAT TO TEST IN A STAGE: routing decisions and side effects.
  - Did it end in the right status?
  - Did it publish the right next job?
  - Did it call the ports it should have?

WHAT NOT TO TEST HERE: whether PyMuPDF parses a PDF correctly. That is the
adapter's business, and testing it here means these tests need real files and
get slow — at which point people stop running them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (Dev A): implement these. Every one uses build_test_container().
#
# === The template method (stages/base.py) — test ONCE, applies to all stages ===
#
# def test_duplicate_delivery_is_a_no_op():
#     Run a job whose resource has already advanced past `accepts`.
#     Assert: nothing changes, NO exception, nothing dead-lettered.
#     THE MOST IMPORTANT TEST IN THE SUITE — at-least-once delivery means this
#     path runs in production regularly.
#
# def test_retryable_error_is_republished_with_backoff():
#     Fake fetcher raises FetchError. Assert the job is back on the queue with
#     not_before set, and NOT in the dead-letter queue.
#
# def test_permanent_error_goes_straight_to_dead_letter():
#     Fake extractor raises ExtractionError. Assert: dead-lettered immediately,
#     NOT retried, resource is FAILED. Retrying a permanent error five times
#     just multiplies the noise.
#
# def test_attempts_are_capped():
#     Always-failing retryable error -> dead-lettered after max_attempts.
#
# def test_next_job_is_published_only_after_the_state_change_is_saved():
#     Ordering matters (see stages/base.py step 7). Use a repository fake that
#     records call order.
#
# === ingest stage ===
#
# def test_duplicate_hash_skips_fetching():
#     -> DUPLICATE, terminal, and the fetcher was never called.
#
# def test_successful_ingest_stores_raw_bytes_and_queues_extract():
#     -> FETCHED, bytes in the object store, "extract" job published.
#
# def test_rerun_with_existing_raw_key_does_not_refetch():
#     Idempotency: re-delivery must not hit the source again.
#
# def test_video_with_captions_records_them_in_metadata():
#     So the extract stage can skip ASR entirely.
#
# === extract stage ===
#
# def test_registry_picks_text_extractor_when_it_can_handle_payload():
#
# def test_falls_back_to_ocr_when_text_extractor_declines():
#     The fallback chain — the reason there are no if-statements in the stage.
#
# def test_output_below_min_chars_raises_extraction_error():
#     Garbage caught here never reaches an MT bill or a reviewer's queue.
# ---------------------------------------------------------------------------
import pytest
import uuid

# These imports would be from the actual backend module
# For now, we'll use relative imports since this is a standalone implementation
import sys
sys.path.insert(0, "C:/Users/WALII/MamaCareAI/MamaCareAI-PT26")

from backend.modules.pipeline.domain.enums import ResourceStatus, SourceType
from backend.modules.pipeline.domain.models import NormalizedDocument, TextBlock, Job
from backend.modules.pipeline.ports.fetcher import FetchResult
from backend.tests.pipeline.fakes import (
    FakeDeduplicator,
    FakeDocumentRepository,
    FakeExtractor,
    FakeFetcher,
    FakeJobQueue,
    FakeObjectStore,
    FakeResourceRepository,
    FakeReviewRepository,
    make_resource,
)
from backend.modules.pipeline.stages.ingest import IngestStage
from backend.modules.pipeline.stages.extract import ExtractStage


# Temporary fake registries for testing (until Dev B completes PIPE-08)
class FakeFetcherRegistry:
    """Temporary fetcher registry for testing - replace with Dev B's implementation."""

    def __init__(self):
        self._fetchers = {}

    def register(self, fetcher):
        self._fetchers[fetcher.source_type] = fetcher

    def get(self, source_type):
        if source_type not in self._fetchers:
            from backend.modules.pipeline.domain.errors import UnsupportedSourceType
            raise UnsupportedSourceType(f"No fetcher for {source_type}")
        return self._fetchers[source_type]


class FakeExtractorRegistry:
    """Temporary extractor registry for testing - replace with Dev B's implementation."""

    def __init__(self):
        self._extractors = []

    def register(self, extractor, priority=50):
        self._extractors.append((priority, extractor))
        self._extractors.sort(key=lambda x: x[0], reverse=True)

    def select(self, content_type, content):
        for priority, extractor in self._extractors:
            if extractor.can_handle(content_type, content):
                return extractor
        from backend.modules.pipeline.domain.errors import ExtractionError
        raise ExtractionError(f"No extractor can handle {content_type}")


def build_test_container():
    """Build a test container with all fakes."""
    resources = FakeResourceRepository()
    documents = FakeDocumentRepository()
    reviews = FakeReviewRepository()
    queue = FakeJobQueue()
    object_store = FakeObjectStore()
    dedup = FakeDeduplicator()

    # Set up registries
    fetcher_registry = FakeFetcherRegistry()
    extractor_registry = FakeExtractorRegistry()

    # Register a fake web fetcher
    test_content = b"<html><body>Test content</body></html>"
    fetcher = FakeFetcher(
        source_type=SourceType.WEB,
        content=test_content,
        content_type="text/html",
        metadata={"title": "Test Page"},
    )
    fetcher_registry.register(fetcher)

    # Register a fake extractor
    test_document = NormalizedDocument(
        resource_id="",  # Will be set by extract stage
        title="Test Document",
        author="Test Author",
        published_date=None,
        blocks=(
            TextBlock(order=0, kind="heading", text="Test Heading"),
            TextBlock(order=1, kind="paragraph", text="Test paragraph content."),
        ),
        source_metadata={},
    )
    extractor = FakeExtractor(document=test_document)
    extractor_registry.register(extractor, priority=100)

    return {
        "resources": resources,
        "documents": documents,
        "reviews": reviews,
        "queue": queue,
        "object_store": object_store,
        "dedup": dedup,
        "fetcher_registry": fetcher_registry,
        "extractor_registry": extractor_registry,
    }


def test_ingest_extract_end_to_end():
    """Test complete flow: SUBMITTED -> FETCHED -> EXTRACTED."""
    container = build_test_container()

    # Create stages
    ingest_stage = IngestStage(
        resources=container["resources"],
        queue=container["queue"],
        reviews=container["reviews"],
        fetchers=container["fetcher_registry"],
        object_store=container["object_store"],
        deduplicator=container["dedup"],
    )

    extract_stage = ExtractStage(
        resources=container["resources"],
        queue=container["queue"],
        reviews=container["reviews"],
        documents=container["documents"],
        extractors=container["extractor_registry"],
        object_store=container["object_store"],
    )

    # Create a SUBMITTED resource
    resource_id = str(uuid.uuid4())
    resource = make_resource(
        resource_id=resource_id,
        source_type=SourceType.WEB,
        source_url="https://example.com/test",
        status=ResourceStatus.SUBMITTED,
    )
    container["resources"].save(resource)

    # Run ingest stage
    ingest_job = Job(
        job_id=str(uuid.uuid4()),
        resource_id=resource_id,
        stage="ingest",
    )
    ingest_stage.run(ingest_job)

    # Verify resource is now FETCHED
    updated_resource = container["resources"].get(resource_id)
    assert updated_resource.status == ResourceStatus.FETCHED
    assert updated_resource.raw_object_key is not None
    assert updated_resource.content_hash is not None

    # Verify object was stored
    stored_content = container["object_store"].get(updated_resource.raw_object_key)
    assert stored_content == b"<html><body>Test content</body></html>"

    # Verify extract job was enqueued
    extract_job = container["queue"].claim_next("extract")
    assert extract_job is not None
    assert extract_job.resource_id == resource_id

    # Run extract stage
    extract_stage.run(extract_job)

    # Verify resource is now EXTRACTED
    final_resource = container["resources"].get(resource_id)
    assert final_resource.status == ResourceStatus.EXTRACTED

    # Verify document was saved
    document = container["documents"].get_document(resource_id)
    assert document is not None
    assert document.title == "Test Document"
    assert len(document.blocks) == 2

    # Verify detect_language job was enqueued
    next_job = container["queue"].claim_next("detect_language")
    assert next_job is not None
    assert next_job.resource_id == resource_id


def test_ingest_idempotency():
    """Test that ingest stage is idempotent - can handle re-delivered jobs."""
    container = build_test_container()

    ingest_stage = IngestStage(
        resources=container["resources"],
        queue=container["queue"],
        reviews=container["reviews"],
        fetchers=container["fetcher_registry"],
        object_store=container["object_store"],
        deduplicator=container["dedup"],
    )

    resource_id = str(uuid.uuid4())
    resource = make_resource(
        resource_id=resource_id,
        source_type=SourceType.WEB,
        source_url="https://example.com/test",
        status=ResourceStatus.SUBMITTED,
    )
    container["resources"].save(resource)

    # Run ingest once
    job1 = Job(job_id=str(uuid.uuid4()), resource_id=resource_id, stage="ingest")
    ingest_stage.run(job1)

    # Get the updated resource
    updated = container["resources"].get(resource_id)
    assert updated.status == ResourceStatus.FETCHED

    # Simulate a re-delivered job (resource already FETCHED)
    job2 = Job(job_id=str(uuid.uuid4()), resource_id=resource_id, stage="ingest")
    ingest_stage.run(job2)

    # Should be a no-op - status should still be FETCHED
    final = container["resources"].get(resource_id)
    assert final.status == ResourceStatus.FETCHED
    assert final.raw_object_key == updated.raw_object_key


def test_url_dedup():
    """Test that URL-level dedup prevents duplicate downloads."""
    container = build_test_container()

    ingest_stage = IngestStage(
        resources=container["resources"],
        queue=container["queue"],
        reviews=container["reviews"],
        fetchers=container["fetcher_registry"],
        object_store=container["object_store"],
        deduplicator=container["dedup"],
    )

    url = "https://example.com/duplicate-test"

    # First resource
    resource1 = make_resource(
        resource_id=str(uuid.uuid4()),
        source_type=SourceType.WEB,
        source_url=url,
        status=ResourceStatus.SUBMITTED,
    )
    container["resources"].save(resource1)

    job1 = Job(job_id=str(uuid.uuid4()), resource_id=resource1.resource_id, stage="ingest")
    ingest_stage.run(job1)

    assert container["resources"].get(resource1.resource_id).status == ResourceStatus.FETCHED

    # Second resource with same URL
    resource2 = make_resource(
        resource_id=str(uuid.uuid4()),
        source_type=SourceType.WEB,
        source_url=url,
        status=ResourceStatus.SUBMITTED,
    )
    container["resources"].save(resource2)

    job2 = Job(job_id=str(uuid.uuid4()), resource_id=resource2.resource_id, stage="ingest")
    ingest_stage.run(job2)

    # Should be marked as DUPLICATE
    assert container["resources"].get(resource2.resource_id).status == ResourceStatus.DUPLICATE


if __name__ == "__main__":
    # Run tests manually for verification
    print("Running test_ingest_extract_end_to_end...")
    test_ingest_extract_end_to_end()
    print("✓ test_ingest_extract_end_to_end passed")

    print("Running test_ingest_idempotency...")
    test_ingest_idempotency()
    print("✓ test_ingest_idempotency passed")

    print("Running test_url_dedup...")
    test_url_dedup()
    print("✓ test_url_dedup passed")

    print("\nAll tests passed!")
