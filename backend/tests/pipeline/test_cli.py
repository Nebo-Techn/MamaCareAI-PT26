"""CLI tests PIPE-21 submit/status + PIPE-30 requeue/reindex/stats."""

from __future__ import annotations

import json
import uuid

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


def test_cli_submit_prints_id(capsys):
    rc = main(["submit", "--url", "https://example.org/guide.pdf", "--type", "pdf"])
    assert rc == 0
    out = capsys.readouterr().out
    assert len(out.strip()) > 0  # resource_id


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
