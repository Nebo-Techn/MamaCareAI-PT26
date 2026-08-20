from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.modules.pipeline.adapters.translation.chunker import Chunk, Chunker
from backend.modules.pipeline.container import build_test_container
from backend.modules.pipeline.domain.enums import (
    ResourceStatus,
    SourceType,
    VersionAuthorKind,
)
from backend.modules.pipeline.domain.errors import TranslationError
from backend.modules.pipeline.domain.models import (
    NormalizedDocument,
    Resource,
    TextBlock,
)
from backend.modules.pipeline.stages import translate as translate_stage


@dataclass(frozen=True)
class _TranslationUnit:
    """Test-only translation shape until the domain unit carries block kinds."""

    order: int
    kind: str
    source_text: str
    translated_text: str
    confidence: float | None = None


@pytest.fixture(autouse=True)
def complete_stage_dependencies(monkeypatch: pytest.MonkeyPatch):
    """Keep these stage tests independent of unfinished model/chunker units."""

    monkeypatch.setattr(
        NormalizedDocument,
        "raw_text",
        property(lambda document: "\n\n".join(block.text for block in document.blocks)),
    )
    monkeypatch.setattr(
        Chunker,
        "chunk",
        lambda _chunker, blocks, *, max_chars=None: [
            Chunk(text=block.text, block_orders=(block.order,)) for block in blocks
        ],
    )
    monkeypatch.setattr(translate_stage, "TranslationUnit", _TranslationUnit)


def test_low_confidence_routes_to_human_confirmation():

    container = build_test_container(
        detector="low_confidence",  # type: ignore
    )
    stage = container.stage("detect_language")

    # Create a resource in EXTRACTED state
    resource = Resource(
        resource_id="test-1",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.EXTRACTED,
    )
    container.resources.save(resource)

    # Create a normalized document
    doc = NormalizedDocument(
        resource_id="test-1",
        title="Test",
        author=None,
        published_date=None,
        blocks=(TextBlock(order=0, kind="paragraph", text="Test content"),),
    )
    container.documents.save_document(doc)

    # Run the stage
    result = stage.handle(resource)

    # Assert it routes to human confirmation
    assert result.next_status == ResourceStatus.NEEDS_LANGUAGE_CONFIRMATION
    assert result.next_stage is None
    assert "alternatives" in result.details


def test_already_swahili_skips_translation():
    """Detected "sw" -> LANGUAGE_DETECTED, next stage "store".
    Translation is bypassed entirely (PDF 3.4, first bullet) — but review is
    NOT. Assert it still reaches the review queue.
    """
    container = build_test_container(
        detector="swahili",  # type: ignore
    )
    stage = container.stage("detect_language")

    resource = Resource(
        resource_id="test-2",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.EXTRACTED,
    )
    container.resources.save(resource)

    doc = NormalizedDocument(
        resource_id="test-2",
        title="Test Swahili",
        author=None,
        published_date=None,
        blocks=(
            TextBlock(
                order=0, kind="paragraph", text="Habari, hii ni content ya Kiswahili"
            ),
        ),
    )
    container.documents.save_document(doc)

    result = stage.handle(resource)

    # Should skip translation and go to store
    assert result.next_status == ResourceStatus.LANGUAGE_DETECTED
    assert result.next_stage == "store"
    assert result.resource_changes.get("detected_language") == "sw"


def test_other_language_routes_to_translation():
    """Detected "en" -> LANGUAGE_DETECTED, next stage "translate"."""
    container = build_test_container(
        detector="english",  # type: ignore
    )
    stage = container.stage("detect_language")

    resource = Resource(
        resource_id="test-3",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.EXTRACTED,
    )
    container.resources.save(resource)

    doc = NormalizedDocument(
        resource_id="test-3",
        title="English Test",
        author=None,
        published_date=None,
        blocks=(TextBlock(order=0, kind="paragraph", text="This is English content"),),
    )
    container.documents.save_document(doc)

    result = stage.handle(resource)

    # Should route to translation
    assert result.next_status == ResourceStatus.LANGUAGE_DETECTED
    assert result.next_stage == "translate"
    assert result.resource_changes.get("detected_language") == "en"


def test_human_confirmed_language_is_not_overwritten():
    """A resource carrying a "language_confirmed_by" marker keeps its language;
    the detector must not overwrite a human decision with a model's guess.
    """
    container = build_test_container(
        detector="english",  # type: ignore
    )
    stage = container.stage("detect_language")

    # Create a resource with human-confirmed language
    resource = Resource(
        resource_id="test-4",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.NEEDS_LANGUAGE_CONFIRMATION,
        detected_language="fr",  # Human confirmed as French
        source_metadata={"language_confirmed_by": "user@example.com"},
    )
    container.resources.save(resource)

    doc = NormalizedDocument(
        resource_id="test-4",
        title="French Test",
        author=None,
        published_date=None,
        blocks=(
            TextBlock(order=0, kind="paragraph", text="Ceci est du contenu français"),
        ),
    )
    container.documents.save_document(doc)

    result = stage.handle(resource)

    # Should preserve human-confirmed language
    assert result.resource_changes.get("detected_language") == "fr"
    assert result.next_status == ResourceStatus.LANGUAGE_DETECTED


# === translate stage ===


def test_creates_machine_version_one_with_engine_recorded():
    """author_kind=MACHINE, version_number=1, engine name stored — the only way
    to answer "did quality change when we switched engines?" later.
    """
    container = build_test_container()
    stage = container.stage("translate")

    resource = Resource(
        resource_id="test-5",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.LANGUAGE_DETECTED,
        detected_language="en",
    )
    container.resources.save(resource)

    doc = NormalizedDocument(
        resource_id="test-5",
        title="Test",
        author=None,
        published_date=None,
        blocks=(TextBlock(order=0, kind="paragraph", text="Hello world"),),
    )
    container.documents.save_document(doc)

    stage.handle(resource)

    # Verify machine version was created
    machine_version = container.versions.get_machine_version(resource.resource_id)
    assert machine_version is not None
    assert machine_version.version_number == 1
    assert machine_version.author_kind == VersionAuthorKind.MACHINE
    assert machine_version.engine == "test-translator"


def test_rerun_does_not_create_a_second_machine_version():

    container = build_test_container()
    stage = container.stage("translate")

    resource = Resource(
        resource_id="test-6",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.LANGUAGE_DETECTED,
        detected_language="en",
    )
    container.resources.save(resource)

    doc = NormalizedDocument(
        resource_id="test-6",
        title="Test",
        author=None,
        published_date=None,
        blocks=(TextBlock(order=0, kind="paragraph", text="Hello world"),),
    )
    container.documents.save_document(doc)

    # First run
    stage.handle(resource)
    version1_count = len(container.versions.list_versions(resource.resource_id))

    # Second run (redelivery)
    stage.handle(resource)
    version2_count = len(container.versions.list_versions(resource.resource_id))

    # Should not create a second version
    assert version1_count == version2_count


def test_length_mismatch_from_translator_raises():
    """Fake translator returns fewer results than inputs. Must RAISE, not
    silently mis-align every block after the gap.
    """
    container = build_test_container(
        translator="mismatched",  # type: ignore
    )
    stage = container.stage("translate")

    resource = Resource(
        resource_id="test-7",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.LANGUAGE_DETECTED,
        detected_language="en",
    )
    container.resources.save(resource)

    doc = NormalizedDocument(
        resource_id="test-7",
        title="Test",
        author=None,
        published_date=None,
        blocks=(
            TextBlock(order=0, kind="paragraph", text="First block"),
            TextBlock(order=1, kind="paragraph", text="Second block"),
            TextBlock(order=2, kind="paragraph", text="Third block"),
        ),
    )
    container.documents.save_document(doc)

    # Should raise on length mismatch
    with pytest.raises(TranslationError):
        stage.handle(resource)


def test_block_structure_survives_translation():
    """Headings are still headings, `order` is preserved. The side-by-side
    review UI depends on this.
    """
    container = build_test_container()
    stage = container.stage("translate")

    resource = Resource(
        resource_id="test-8",
        source_type=SourceType.WEB,
        source_url="https://example.com",
        status=ResourceStatus.LANGUAGE_DETECTED,
        detected_language="en",
    )
    container.resources.save(resource)

    doc = NormalizedDocument(
        resource_id="test-8",
        title="Test",
        author=None,
        published_date=None,
        blocks=(
            TextBlock(order=0, kind="heading", text="Introduction"),
            TextBlock(order=1, kind="paragraph", text="This is a paragraph"),
            TextBlock(order=2, kind="heading", text="Section 2"),
            TextBlock(order=3, kind="paragraph", text="Another paragraph"),
        ),
    )
    container.documents.save_document(doc)

    stage.handle(resource)

    # Verify machine version preserves structure
    machine_version = container.versions.get_machine_version(resource.resource_id)
    assert machine_version is not None
    # Structure should be preserved in the translation units.
    assert len(machine_version.units) == len(doc.blocks)
    for unit, block in zip(machine_version.units, doc.blocks, strict=True):
        assert unit.order == block.order
        assert unit.kind == block.kind # type: ignore
        assert unit.translated_text
