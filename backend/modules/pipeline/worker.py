"""
Worker entrypoint — runs ONE stage as its own process.

    python -m backend.modules.pipeline.worker --stage extract

WHY ONE STAGE PER PROCESS (PDF section 4, Scalability)
The stages have wildly different resource profiles. ASR and OCR are CPU/GPU
heavy and bursty; language detection and database writes are cheap and
constant. Running them in one process means scaling the cheap stages just to
get more of the expensive one — you pay for eight idle detector workers to get
eight transcription workers.

Separate processes mean separate scaling rules, and one crashing ASR worker
cannot take PDF extraction down with it.

DEPLOYMENT: one container image, different `--stage` arguments. In Kubernetes
that is one Deployment per stage, each with its own replica count and its own
HPA. Do not build seven images.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Consume jobs for one stage until told to stop.

    TODO (junior dev) — implement in this order:

      1. PARSE ARGS: --stage (required), --max-jobs (optional, for testing).

      2. CONFIGURE LOGGING as structured JSON, and put `resource_id` and
         `stage` on EVERY log line. When something goes wrong in production the
         first question is always "what happened to resource X?", and the only
         acceptable answer is one grep.

      3. BUILD THE CONTAINER ONCE, before the loop:
             container = build_container()
             stage = container.stage(args.stage)
         Never inside the loop — that reloads the MT model on every job.

      4. INSTALL A GRACEFUL SHUTDOWN HANDLER:
             signal.signal(SIGTERM, ...) -> set a `stop` flag
         On SIGTERM, FINISH the current job, then exit. Do not abandon it
         mid-flight. Kubernetes sends SIGTERM before every rolling deploy, so
         this path runs constantly — an abrupt exit leaves a half-processed
         resource and an unacked message on every single deploy.

      5. THE CONSUME LOOP:
             for handle in container.queue.consume(stage.name):
                 if stop_requested: break
                 with handle as job:
                     stage.run(job)
         Note how little is here. All retry/ack/transition logic lives in
         `stages/base.py`, so this loop stays five lines and every stage gets
         identical semantics.

      6. HEALTH: expose a liveness signal (a touched file or a tiny HTTP
         endpoint) so the orchestrator can restart a wedged worker. A worker
         that is alive but stuck on a hung socket is worse than a dead one —
         the dead one gets restarted.

      7. RETURN 0 on clean shutdown, non-zero on fatal startup failure (bad
         stage name, missing credentials). Fail loudly at startup, not silently
         at the first job.
    """
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
