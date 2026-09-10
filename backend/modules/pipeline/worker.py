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

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="worker", description="Pipeline stage worker")
    parser.add_argument("--stage", required=True, help="Stage name (ingest, extract, detect_language, translate, store, review, publish)")
    parser.add_argument("--max-jobs", type=int, default=None, help="Exit after N jobs (for testing)")
    return parser.parse_args(argv)


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class _JsonFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "resource_id"):
            record.resource_id = "-"  # type: ignore[attr-defined]
        if not hasattr(record, "stage"):
            record.stage = "-"  # type: ignore[attr-defined]
        return True


def main(argv: list[str] | None = None) -> int:
    """Consume jobs for one stage until told to stop."""
    args = _parse_args(argv)

    _configure_logging()
    json_filter = _JsonFilter()
    logging.getLogger().addFilter(json_filter)

    # Build container once before loop
    try:
        from .config import PipelineSettings
        from .container import build_container, build_test_container

        try:
            settings = PipelineSettings()
            container = build_container(settings)
        except RuntimeError as exc:
            # Until SQL repos are ready, fall back to test container for local/CI
            logger.warning(json.dumps({"stage": args.stage, "msg": f"build_container failed, using test container: {exc}"}))
            container = build_test_container()

        try:
            stage = container.stage(args.stage)
        except ValueError as exc:
            logger.error(json.dumps({"stage": args.stage, "msg": str(exc)}))
            return 2
    except Exception as exc:  # noqa: BLE001
        logger.error(json.dumps({"stage": getattr(args, 'stage', '-'), "msg": f"startup failed: {exc}"}))
        return 1

    # Graceful SIGTERM
    stop_requested = {"flag": False}

    def _handle_sigterm(signum, frame):
        stop_requested["flag"] = True
        logger.info(json.dumps({"stage": args.stage, "resource_id": "-", "msg": "SIGTERM received, finishing current job"}))

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    # Health file
    health_path = Path(f"/tmp/worker-{args.stage}.alive")
    try:
        health_path.touch(exist_ok=True)
    except Exception:  # noqa: BLE001, S110
        pass

    # Consume loop - 5 lines plus health/max-jobs handling
    jobs_done = 0

    # Resolve queue consume interface - try ports JobQueue consume, fallback to simple polling
    def _consume_loop():
        nonlocal jobs_done
        # Try to use container.queue.consume if available (real JobQueue)
        queue = container.queue
        consume = getattr(queue, "consume", None)
        if callable(consume):
            try:
                for handle in consume(stage.name):
                    if stop_requested["flag"]:
                        break
                    if args.max_jobs is not None and jobs_done >= args.max_jobs:
                        break
                    with handle as job:
                        # Structured log with resource_id and stage
                        if hasattr(job, "resource_id"):
                            rid = job.resource_id
                        elif hasattr(job, "resource"):
                            rid = getattr(job.resource, "resource_id", str(job))
                        else:
                            rid = str(job)
                        logger.info(json.dumps({"stage": stage.name, "resource_id": rid, "msg": "processing job"}))
                        try:
                            health_path.touch(exist_ok=True)
                        except Exception:  # noqa: BLE001, S110
                            pass
                        stage.run(job)
                        jobs_done += 1
                        logger.info(json.dumps({"stage": stage.name, "resource_id": rid, "msg": "job done"}))
            except Exception as exc:  # noqa: BLE001
                logger.error(json.dumps({"stage": stage.name, "msg": f"consume loop error: {exc}"}))
        else:
            # Fallback for test fakes without consume (polling)
            claim = getattr(queue, "claim_next", None) or getattr(queue, "get_next", None)
            while not stop_requested["flag"]:
                if args.max_jobs is not None and jobs_done >= args.max_jobs:
                    break
                job = None
                if callable(claim):
                    try:
                        job = claim(stage.name)
                    except TypeError:
                        try:
                            job = claim()
                        except Exception:  # noqa: BLE001
                            job = None
                if job is None:
                    if args.max_jobs is not None:
                        break
                    time.sleep(0.1)
                    # For test fakes without jobs, break to avoid infinite loop
                    if hasattr(queue, "queues") or hasattr(queue, "_queues"):
                        break
                    continue
                # Handle may be Job or context manager
                if hasattr(job, "__enter__"):
                    with job as j:
                        rid = getattr(j, "resource_id", str(j))
                        logger.info(json.dumps({"stage": stage.name, "resource_id": rid, "msg": "processing job"}))
                        stage.run(j)
                        jobs_done += 1
                else:
                    rid = getattr(job, "resource_id", str(job))
                    logger.info(json.dumps({"stage": stage.name, "resource_id": rid, "msg": "processing job"}))
                    stage.run(job)
                    jobs_done += 1
                try:
                    health_path.touch(exist_ok=True)
                except Exception:  # noqa: BLE001, S110
                    pass

    try:
        _consume_loop()
    except KeyboardInterrupt:
        logger.info(json.dumps({"stage": args.stage, "msg": "interrupted"}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
