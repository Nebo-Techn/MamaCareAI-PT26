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

import sys


def main(argv: list[str] | None = None) -> int:
    """Dispatch a pipeline management command.

    TODO (junior dev) — implement these subcommands, roughly in this order of
    usefulness:

      submit    --url --type [--metadata]
                Calls SubmissionService.submit(). Prints the resource_id.
                Your everyday manual-testing command; build it first.

      status    --resource-id
                Prints current status, timestamps, attempt count, last error,
                and version history. The first thing you run when someone asks
                "what happened to this document?".

      requeue   --stage --failed | --resource-id
                Re-drives dead-lettered jobs after a provider outage.
                IMPORTANT: create a NEW resource_id rather than resurrecting a
                FAILED one (FAILED is terminal in the state machine, on
                purpose). The failed attempt stays in the record; re-driving
                must not erase the evidence of what went wrong.

      reindex   [--since]
                Rebuilds the search index from the database. Proves the index
                is a derived read model rather than a second source of truth.
                RUN IT ONCE EARLY, while it is cheap to fix if it is broken.

      export-feedback --since [--out]
                FeedbackExporter.export_jsonl(). The MT/human training pairs.

      stats     Queue depth per stage, counts per status, oldest item in
                review. The 30-second "is the pipeline healthy?" check.

    Use argparse subparsers. Return 0 on success, non-zero on failure, and
    print errors to stderr — these commands will end up in shell scripts and in
    CI, where exit codes are the only thing that gets checked.
    """
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
