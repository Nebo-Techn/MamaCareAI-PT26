"""CLI tests PIPE-21 submit/status + PIPE-30 requeue/reindex/stats."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import backend.modules.pipeline.cli as cli_module
from backend.modules.pipeline.cli import main
from backend.modules.pipeline.container import build_test_container
from backend.modules.pipeline.domain.enums import (
    ResourceStatus,
    SourceType,
    VersionAuthorKind,
)
from backend.modules.pipeline.domain.models import (
    ContentVersion,
    Job,
    JobStatus,
    NormalizedDocument,
    Resource,
    TextBlock,
    TranslationUnit,
)
from backend.modules.pipeline.ports.fetcher import FetchResult
from backend.modules.pipeline.ports.language_detector import DetectionResult
from backend.modules.pipeline.ports.translator import TranslatedChunk


def test_cli_submit_prints_id(capsys):
    rc = main(["submit", "--url", "https://example.org/guide.pdf", "--type", "pdf"])
    assert rc == 0
    out = capsys.readouterr().out
    assert len(out.strip()) > 0  # resource_id


def _patch_process_url_adapters(monkeypatch, *, language: str) -> SimpleNamespace:
    from backend.modules.pipeline import container as container_module

    document = NormalizedDocument(
        resource_id="cli-process-url",
        title="Guide",
        author=None,
        published_date=None,
        blocks=(TextBlock(order=0, kind="paragraph", text="The guide is useful."),),
        source_metadata={},
    )

    class Fetcher:
        def fetch(self, url):
            return FetchResult(b"<p>The guide is useful.</p>", "text/html")

    class Fetchers:
        def get(self, source_type):
            return Fetcher()

    class Extractor:
        def extract(self, resource_id, content, *, metadata):
            return document

    class Extractors:
        def select(self, content_type, content):
            return Extractor()

    class Detector:
        def detect(self, text):
            return DetectionResult(language=language, confidence=0.99)

    class Translator:
        engine_name = "fake"

        def __init__(self):
            self.calls = 0

        def supports(self, source_language, target_language):
            return True

        def translate_batch(self, texts, *, source_language, target_language="sw"):
            self.calls += 1
            return [TranslatedChunk("Mwongozo ni muhimu.") for _ in texts]

    translator = Translator()
    monkeypatch.setattr(container_module, "build_fetchers", lambda settings: Fetchers())
    monkeypatch.setattr(container_module, "build_extractors", lambda settings: Extractors())
    monkeypatch.setattr(container_module, "build_detector", lambda settings: Detector())
    monkeypatch.setattr(container_module, "build_translator", lambda settings: translator)
    monkeypatch.setattr(
        "backend.modules.pipeline.services.submission.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 0))],
    )
    return SimpleNamespace(translator=translator)


def test_process_url_translates_english(capsys, monkeypatch):
    adapters = _patch_process_url_adapters(monkeypatch, language="en")

    rc = main(["process-url", "--url", "https://example.org/guide"])

    assert rc == 0
    assert capsys.readouterr().out.strip() == (
        "=== ORIGINAL (en) ===\n"
        "The guide is useful.\n\n"
        "=== TRANSLATED (sw) ===\n"
        "Mwongozo ni muhimu."
    )
    assert adapters.translator.calls == 1


def test_process_url_leaves_non_english_unchanged(capsys, monkeypatch):
    adapters = _patch_process_url_adapters(monkeypatch, language="sw")

    rc = main(["process-url", "--url", "https://example.org/guide"])

    assert rc == 0
    assert capsys.readouterr().out.strip() == (
        "=== ORIGINAL (sw) ===\n"
        "The guide is useful.\n\n"
        "=== TRANSLATED (sw) ===\n"
        "Translation skipped: detected language is not English."
    )
    assert adapters.translator.calls == 0


def test_cli_status_not_found():
    rc = main(["status", "--resource-id", "does-not-exist-123"])
    assert rc != 0


def _make_failed_resource() -> Resource:
    return Resource(
        resource_id=str(uuid.uuid4()),
        source_type=SourceType.WEB,
        source_url="https://example.org/failed-page",
        status=ResourceStatus.FAILED,
        last_error="boom",
        attempt_count=5,
    )


def test_cli_requeue_empty_returns_zero(capsys, monkeypatch):
    container = build_test_container()
    monkeypatch.setattr(
        cli_module, "_build_container_for_cli", lambda: container
    )
    rc = main(["requeue", "--stage", "translate"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["requeued"] == 0


def test_cli_requeue_dead_letter_republishes(capsys, monkeypatch):
    container = build_test_container()
    job = Job(
        job_id=str(uuid.uuid4()),
        resource_id=str(uuid.uuid4()),
        stage="translate",
        status=JobStatus.PENDING,
    )
    container.queue.send_to_dead_letter(job, reason="provider outage")
    monkeypatch.setattr(
        cli_module, "_build_container_for_cli", lambda: container
    )
    rc = main(["requeue", "--stage", "translate"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["requeued"] == 1
    assert container.queue.depth("translate") == 1


def test_cli_requeue_failed_restarts_at_ingest(capsys, monkeypatch):
    container = build_test_container()
    resource = _make_failed_resource()
    container.resources.add(resource)
    monkeypatch.setattr(
        cli_module, "_build_container_for_cli", lambda: container
    )
    rc = main(["requeue", "--failed"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["requeued"] == 1
    assert out["restart_at"] == "ingest"
    reset = container.resources.get(resource.resource_id)
    assert reset.status == ResourceStatus.SUBMITTED
    assert container.queue.depth("ingest") == 1


def test_cli_requeue_bad_stage():
    rc = main(["requeue", "--stage", "nope"])
    assert rc == 1


def _seed_indexable_resource(container) -> str:
    rid = str(uuid.uuid4())
    container.resources.add(
        Resource(
            resource_id=rid,
            source_type=SourceType.WEB,
            source_url="https://example.org/swahili-guide",
            status=ResourceStatus.TRANSLATED,
        )
    )
    container.documents.save_document(
        NormalizedDocument(
            resource_id=rid,
            title="Swahili Guide",
            author=None,
            published_date=None,
            blocks=(TextBlock(order=0, kind="paragraph", text="source"),),
            source_metadata={},
        )
    )
    container.versions.save_version(
        ContentVersion(
            version_id=str(uuid.uuid4()),
            resource_id=rid,
            version_number=1,
            author_kind=VersionAuthorKind.MACHINE,
            author_id=None,
            units=(
                TranslationUnit(
                    order=0, source_text="hello", translated_text="habari"
                ),
            ),
            engine="test",
        )
    )
    return rid


def test_cli_reindex_indexes_published_content(capsys, monkeypatch):
    container = build_test_container()
    rid = _seed_indexable_resource(container)
    monkeypatch.setattr(
        cli_module, "_build_container_for_cli", lambda: container
    )
    rc = main(["reindex"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["indexed"] == 1
    assert rid in container.search.items


def test_cli_reindex_bad_since():
    rc = main(["reindex", "--since", "not-a-date"])
    assert rc == 1


def test_cli_stats_reports_queues_and_counts(capsys, monkeypatch):
    container = build_test_container()
    monkeypatch.setattr(
        cli_module, "_build_container_for_cli", lambda: container
    )
    rc = main(["stats"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert set(out["queues"]) == {
        "ingest",
        "extract",
        "detect_language",
        "translate",
        "store",
        "review",
        "publish",
    }
    assert "dead_letter" in out
    assert "resources" in out


def test_cli_export_feedback_still_deferred():
    rc = main(["export-feedback", "--since", "2026-01-01"])
    assert rc == 2
