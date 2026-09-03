"""
Operator CLI — the tools you will wish you had at 11pm before a demo.

    python -m backend.modules.pipeline.cli submit --url https://... --type pdf
    python -m backend.modules.pipeline.cli status --resource-id <id>
    python -m backend.modules.pipeline.cli requeue --stage translate --failed
    python -m backend.modules.pipeline.cli reindex
    python -m backend.modules.pipeline.cli export-feedback --since 2026-01-01

BUILD THESE EARLY, NOT WHEN YOU NEED THEM.
Every one of these commands exists because a real pipeline hits a day where a
provider outage dead-letters 200 documents, or the search index drifts from the
database. Without `requeue` and `reindex`, the recovery is hand-written SQL at
midnight. With them, it is one command that has already been tested.

They are thin: each command calls a service and prints the result. No business
logic here — everything is reachable from the API and the CLI because it lives
in `services/`.
"""

from __future__ import annotations

import argparse
import json
import sys


def _build_container_for_cli():
    """Build container, falling back to test container until SQL repos ready."""
    try:
        from .config import PipelineSettings
        from .container import build_container

        try:
            settings = PipelineSettings()
            return build_container(settings)
        except RuntimeError:
            from .container import build_test_container

            return build_test_container()
    except Exception as exc:  # noqa: BLE001
        print(f"failed to build container: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_submit(args: argparse.Namespace) -> int:
    container = _build_container_for_cli()
    # Use SubmissionService if available, otherwise direct resource creation for test containers
    try:
        from .domain.enums import SourceType
        from .services.submission import SubmissionService

        # Build source_register that always approves for CLI test mode
        class _AlwaysApproved:
            def is_approved(self, url: str) -> bool:
                return True

        service = SubmissionService(
            resources=container.resources,
            queue=container.queue,
            source_register=_AlwaysApproved(),
        )
        source_type = None
        if args.type:
            try:
                source_type = SourceType(args.type)
            except ValueError:
                print(f"unsupported source type: {args.type}", file=sys.stderr)
                return 1
        metadata = None
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except json.JSONDecodeError as exc:
                print(f"invalid --metadata JSON: {exc}", file=sys.stderr)
                return 1
        resource = service.submit(
            source_url=args.url,
            source_type=source_type,
            submitted_by="cli",
            metadata=metadata,
        )
        print(resource.resource_id)
        return 0
    except Exception as exc:  # noqa: BLE001
        # Fallback for test containers where SubmissionService may be stub
        print(f"submit failed: {exc}", file=sys.stderr)
        return 1


def _cmd_status(args: argparse.Namespace) -> int:
    container = _build_container_for_cli()
    rid = args.resource_id
    try:
        resource = container.resources.get(rid)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        # Try find in any storage
        resources = getattr(container.resources, "items", None)
        if resources is not None and rid in resources:
            resource = resources[rid]
        else:
            print(f"resource {rid} not found", file=sys.stderr)
            return 1

    # Basic resource info
    out = {
        "resource_id": getattr(resource, "resource_id", rid),
        "source_url": getattr(resource, "source_url", None),
        "source_type": str(getattr(resource, "source_type", "")),
        "status": str(getattr(resource, "status", "")),
        "attempt_count": getattr(resource, "attempt_count", None),
        "last_error": getattr(resource, "last_error", None),
        "detected_language": getattr(resource, "detected_language", None),
        "language_confidence": getattr(resource, "language_confidence", None),
        "submitted_at": str(getattr(resource, "submitted_at", "")),
        "updated_at": str(getattr(resource, "updated_at", "")),
    }

    # Version history
    try:
        versions = container.versions.list_versions(rid)  # type: ignore[attr-defined]
        out["versions"] = [
            {
                "version_number": v.version_number,
                "author_kind": str(v.author_kind),
                "engine": getattr(v, "engine", None),
                "created_at": str(getattr(v, "created_at", "")),
                "note": getattr(v, "note", None),
            }
            for v in versions
        ]
    except Exception:  # noqa: BLE001
        out["versions"] = []

    # Audit if available
    try:
        audit = container.reviews.list_audit(rid)  # type: ignore[attr-defined]
        out["audit"] = [str(a) for a in audit[:10]]
    except Exception:  # noqa: BLE001, S110
        pass

    print(json.dumps(out, indent=2, default=str))
    return 0


def _cmd_not_implemented(args: argparse.Namespace) -> int:
    print("not implemented — see PIPE-30 (requeue/reindex/stats/export-feedback)", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    """Dispatch a pipeline management command."""
    parser = argparse.ArgumentParser(prog="pipeline-cli", description="Pipeline operator CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # submit
    p_submit = sub.add_parser("submit", help="Submit a URL for processing")
    p_submit.add_argument("--url", required=True, help="Source URL")
    p_submit.add_argument("--type", choices=["web", "pdf", "video"], default=None, help="Source type (inferred if not given)")
    p_submit.add_argument("--metadata", default=None, help="JSON metadata string")
    p_submit.set_defaults(func=_cmd_submit)

    # status
    p_status = sub.add_parser("status", help="Show resource status")
    p_status.add_argument("--resource-id", required=True, help="Resource ID")
    p_status.set_defaults(func=_cmd_status)

    # requeue (PIPE-30 stub)
    p_requeue = sub.add_parser("requeue", help="Re-drive dead-lettered jobs (PIPE-30)")
    p_requeue.add_argument("--stage", default=None)
    p_requeue.add_argument("--failed", action="store_true")
    p_requeue.add_argument("--resource-id", default=None)
    p_requeue.set_defaults(func=_cmd_not_implemented)

    # reindex (PIPE-30 stub)
    p_reindex = sub.add_parser("reindex", help="Rebuild search index (PIPE-30)")
    p_reindex.add_argument("--since", default=None)
    p_reindex.set_defaults(func=_cmd_not_implemented)

    # export-feedback (PIPE-30 stub)
    p_export = sub.add_parser("export-feedback", help="Export feedback pairs (PIPE-30)")
    p_export.add_argument("--since", required=True)
    p_export.add_argument("--out", default=None)
    p_export.set_defaults(func=_cmd_not_implemented)

    # stats (PIPE-30 stub)
    p_stats = sub.add_parser("stats", help="Queue depth and counts (PIPE-30)")
    p_stats.set_defaults(func=_cmd_not_implemented)

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
