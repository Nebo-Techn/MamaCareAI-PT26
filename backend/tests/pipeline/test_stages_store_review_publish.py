"""
Tests for the store, review, and publish stages (PIPE-11).

**Owner: Dev C** (see the Sprint 1 split in `docs/PIPELINE_BACKLOG.md`).

Fakes live in this file for now — `tests/pipeline/fakes.py` is Dev A's PIPE-06
file and is still a template. When it lands, these tests should switch to
`build_test_container()` without changing what they assert.

What is covered, per the plan:
  - StoreStage indexes BOTH the "has an MT version" path and the
    "already-Swahili, no version" path (the easy-to-miss one).
  - StoreStage opens exactly one review assignment.
  - ReviewStage always returns next_stage=None (the pipeline parks here).
  - PublishStage blocks on a failed compliance check and never publishes.
  - PublishStage publishes the LATEST version, not version 1, when a human
    edit exists — the worst-bug guard.
  - PublishStage records who approved and which version in its details.
"""

from __future__ import annotations

import pytest

from modules.pipeline.domain.enums import ResourceStatus, SourceType, VersionAuthorKind
from modules.pipeline.domain.models import (
    ContentVersion,
    NormalizedDocument,
    Resource,
    ReviewAssignment,
    TextBlock,
    TranslationUnit,
)
from modules.pipeline.ports.search_index import IndexedResource
from modules.pipeline.stages.publish import PublishStage
from modules.pipeline.stages.review import ReviewStage
from modules.pipeline.stages.store import StoreStage


# --- fakes (see file docstring) ----------------------------------------------


class FakeVersionRepository:
    def __init__(self, versions: dict[str, list[ContentVersion]] | None = None) -> None:
        self._by_resource: dict[str, list[ContentVersion]] = versions or {}

    def save_version(self, version: ContentVersion) -> None:
        self._by_resource.setdefault(version.resource_id, []).append(version)

    def get_latest(self, resource_id: str) -> ContentVersion | None:
        versions = self._by_resource.get(resource_id, [])
        return max(versions, key=lambda v: v.version_number) if versions else None


class FakeDocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, NormalizedDocument] = {}

    def save_document(self, document: NormalizedDocument) -> None:
        self._documents[document.resource_id] = document

    def get_document(self, resource_id: str) -> NormalizedDocument:
        return self._documents[resource_id]


class FakeSearchIndex:
    def __init__(self) -> None:
        self.indexed: dict[str, IndexedResource] = {}

    def index(self, resource: IndexedResource) -> None:
        self.indexed[resource.resource_id] = resource

    def search(self, query: str, *, limit: int = 20, offset: int = 0) -> list:
        return []


class FakeReviewService:
    def __init__(self) -> None:
        self.assignments: dict[str, ReviewAssignment] = {}
        self.calls: list[tuple[Resource, ContentVersion | None]] = []

    def enqueue_for_review(
        self, resource: Resource, version: ContentVersion | None
    ) -> ReviewAssignment:
        self.calls.append((resource, version))
        existing = self.assignments.get(resource.resource_id)
        if existing is not None:
            return existing
        assignment = ReviewAssignment(
            assignment_id=f"a-{resource.resource_id}",
            resource_id=resource.resource_id,
            reviewer_id=None,  # unclaimed
        )
        self.assignments[resource.resource_id] = assignment
        return assignment


class FakeComplianceGate:
    def __init__(self, *, allowed: bool, reason: str | None = None) -> None:
        self._allowed = allowed
        self._reason = reason

    def evaluate(self, resource: Resource):
        from modules.pipeline.services.compliance import ComplianceDecision

        return ComplianceDecision(allowed=self._allowed, reason=self._reason)


class FakeResourceRepository:
    def get(self, resource_id: str) -> Resource:
        raise NotImplementedError


class FakeJobQueue:
    def publish(self, job) -> None:
        self.published = getattr(self, "published", [])
        self.published.append(job)


class FakeReviewRepository:
    pass


# --- builders ----------------------------------------------------------------


def make_resource(*, status: ResourceStatus, **overrides) -> Resource:
    fields = {
        "resource_id": "r1",
        "source_type": SourceType.WEB,
        "source_url": "https://example.org/article",
        "status": status,
        "source_metadata": {},
    }
    fields.update(overrides)
    return Resource(**fields)


def make_version(
    *, resource_id: str = "r1", version_number: int = 1, text: str = "translated"
) -> ContentVersion:
    return ContentVersion(
        version_id=f"v{resource_id}-{version_number}",
        resource_id=resource_id,
        version_number=version_number,
        author_kind=VersionAuthorKind.HUMAN if version_number > 1 else VersionAuthorKind.MACHINE,
        author_id=None if version_number == 1 else "reviewer-7",
        units=(
            TranslationUnit(order=0, source_text="source", translated_text=text),
        ),
    )


def make_document(*, resource_id: str = "r1") -> NormalizedDocument:
    return NormalizedDocument(
        resource_id=resource_id,
        title="Already-Swahili title",
        author=None,
        published_date=None,
        blocks=(
            TextBlock(order=0, kind="paragraph", text="Habari za afya ya mama."),
            TextBlock(order=1, kind="paragraph", text="Tafadhali wasiliana na daktari."),
        ),
    )


def build_store_stage(**overrides) -> tuple[StoreStage, FakeSearchIndex, FakeReviewService]:
    search = FakeSearchIndex()
    review_service = FakeReviewService()
    versions = overrides.get("versions") or FakeVersionRepository()
    documents = overrides.get("documents") or FakeDocumentRepository()
    stage = StoreStage(
        resources=FakeResourceRepository(),
        queue=FakeJobQueue(),
        reviews=FakeReviewRepository(),
        documents=documents,
        versions=versions,
        search=search,
        review_service=review_service,
    )
    return stage, search, review_service


def build_publish_stage(**overrides) -> tuple[PublishStage, FakeSearchIndex]:
    search = FakeSearchIndex()
    compliance = overrides.get("compliance") or FakeComplianceGate(allowed=True)
    versions = overrides.get("versions") or FakeVersionRepository()
    stage = PublishStage(
        resources=FakeResourceRepository(),
        queue=FakeJobQueue(),
        reviews=FakeReviewRepository(),
        versions=versions,
        search=search,
        compliance_gate=compliance,
    )
    return stage, search


# --- store stage -------------------------------------------------------------


def test_store_indexes_versioned_path_and_opens_one_assignment() -> None:
    versions = FakeVersionRepository()
    versions.save_version(make_version(resource_id="r1", version_number=1))
    stage, search, review_service = build_store_stage(versions=versions)

    result = stage.handle(
        make_resource(status=ResourceStatus.TRANSLATED, source_metadata={"title": "T"})
    )

    assert result.next_status == ResourceStatus.STORED
    assert result.next_stage == "review"
    indexed = search.indexed["r1"]
    assert indexed.translated_text == "translated"
    assert indexed.version_number == 1
    assert indexed.status == "stored"
    assert len(review_service.calls) == 1
    assert len(review_service.assignments) == 1


def test_store_already_swahili_path_indexes_document_directly() -> None:
    documents = FakeDocumentRepository()
    documents.save_document(make_document())
    versions = FakeVersionRepository()  # deliberately empty: no MT version
    stage, search, review_service = build_store_stage(
        versions=versions, documents=documents
    )

    result = stage.handle(make_resource(status=ResourceStatus.LANGUAGE_DETECTED))

    assert result.next_status == ResourceStatus.STORED
    indexed = search.indexed["r1"]
    assert indexed.title == "Already-Swahili title"
    assert "Habari za afya ya mama" in indexed.translated_text
    assert indexed.version_number == 0
    assert len(review_service.assignments) == 1


def test_store_handle_running_twice_does_not_double_the_review_assignments() -> None:
    versions = FakeVersionRepository()
    versions.save_version(make_version())
    stage, search, review_service = build_store_stage(versions=versions)
    resource = make_resource(status=ResourceStatus.TRANSLATED)

    stage.handle(resource)
    stage.handle(resource)  # at-least-once delivery: the job can run twice

    assert len(review_service.assignments) == 1


# --- review stage ------------------------------------------------------------


def test_review_stage_moves_to_in_review_and_stops() -> None:
    stage = ReviewStage(
        resources=FakeResourceRepository(),
        queue=FakeJobQueue(),
        reviews=FakeReviewRepository(),
    )

    result = stage.handle(make_resource(status=ResourceStatus.STORED))

    assert result.next_status == ResourceStatus.IN_REVIEW
    assert result.next_stage is None  # a human, not a worker, drives it from here


# --- publish stage -----------------------------------------------------------


def test_publish_stage_blocks_on_compliance_failure_and_never_publishes() -> None:
    compliance = FakeComplianceGate(allowed=False, reason="unknown licence")
    versions = FakeVersionRepository()
    versions.save_version(make_version())
    stage, search = build_publish_stage(compliance=compliance, versions=versions)

    result = stage.handle(make_resource(status=ResourceStatus.APPROVED))

    assert result.next_status == ResourceStatus.BLOCKED_LICENSING
    assert result.next_stage is None
    assert result.details["reason"] == "unknown licence"
    assert "r1" not in search.indexed


def test_publish_stage_publishes_the_latest_version_not_version_one() -> None:
    versions = FakeVersionRepository()
    versions.save_version(make_version(version_number=1, text="machine"))
    versions.save_version(make_version(version_number=2, text="human-edited"))
    stage, search = build_publish_stage(versions=versions)

    result = stage.handle(
        make_resource(
            status=ResourceStatus.APPROVED,
            source_metadata={"approved_by": "reviewer-7"},
        )
    )

    assert result.next_status == ResourceStatus.PUBLISHED
    indexed = search.indexed["r1"]
    assert indexed.version_number == 2
    assert indexed.translated_text == "human-edited"
    assert indexed.status == "published"


def test_publish_stage_records_who_approved_and_which_version() -> None:
    versions = FakeVersionRepository()
    versions.save_version(make_version(version_number=2, text="approved"))
    stage, search = build_publish_stage(versions=versions)

    result = stage.handle(
        make_resource(
            status=ResourceStatus.APPROVED,
            source_metadata={"approved_by": "reviewer-7"},
        )
    )

    assert result.details["approved_by"] == "reviewer-7"
    assert result.details["approved_version"] == 2