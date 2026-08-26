"""
AWS SQS queue — the production backend (PDF: "Kafka or AWS SQS").

Recommended over Kafka unless measured throughput demands otherwise: it is
managed, it has a built-in dead-letter queue and visibility timeouts, and there
are no brokers to operate. For a four-person team with an 8-week window, "no
brokers to operate" is a decisive advantage.

ONE QUEUE PER STAGE. That is what lets each stage scale independently — the
whole point of the architecture. Do not put all stages on one queue with a
type field; you lose independent scaling and one slow stage starves the rest.

THE THREE SQS FACTS THAT WILL BITE YOU
  1. VISIBILITY TIMEOUT must exceed the stage's worst-case runtime. If ASR
     takes 10 minutes and the timeout is 5, SQS redelivers the job while it is
     still being worked on and you transcribe it twice, in parallel, forever.
     Set it per stage, and extend the heartbeat for long jobs.
  2. AT-LEAST-ONCE delivery. Duplicates are normal. Idempotent stages plus the
     state machine are what make that safe — which is already the design.
  3. MAX 256KB per message. Never put document content in a message. Jobs
     carry an id and a stage name, which is exactly why `Job` is tiny.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from importlib import import_module
from math import ceil
from typing import Any

from ...domain.enums import JobStatus
from ...domain.models import Job
from ...ports.job_queue import JobQueue

logger = logging.getLogger(__name__)


class SqsQueue(JobQueue):
    """Queue backed by AWS SQS, one queue URL per stage."""

    def __init__(
        self,
        *,
        queue_urls: dict[str, str],  # stage name -> queue URL
        dead_letter_url: str,
        region: str,
        visibility_timeout: int = 300,
        wait_time_seconds: int = 20,     # long polling — see below
        client: Any | None = None,
    ) -> None:
        if visibility_timeout < 0 or visibility_timeout > 43_200:
            raise ValueError("visibility_timeout must be between 0 and 43200 seconds")
        if wait_time_seconds < 0 or wait_time_seconds > 20:
            raise ValueError("wait_time_seconds must be between 0 and 20 seconds")

        self._queue_urls = queue_urls
        self._dead_letter_url = dead_letter_url
        self._visibility_timeout = visibility_timeout
        # 20s is the maximum and the right default: long polling means one API
        # call per 20 seconds of idle instead of one per 100ms. On SQS's
        # per-request pricing, short polling on an idle queue costs real money
        # to receive nothing.
        self._wait_time = wait_time_seconds
        if client is None:
            try:
                boto3 = import_module("boto3")
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "boto3 is required to use SqsQueue; install backend/requirements.txt"
                ) from exc
            resolved_client = boto3.client("sqs", region_name=region)
        else:
            resolved_client = client
        self._client: Any = resolved_client

    def publish(self, job: Job) -> None:
        """Publish a small JSON job, using SQS delay for short retries."""
        queue_url = self._queue_urls.get(job.stage)
        if queue_url is None:
            raise ValueError(f"Unknown queue stage: {job.stage}")

        delay_seconds = 0
        if job.not_before is not None:
            delay_seconds = max(
                0,
                ceil((job.not_before - datetime.now(UTC)).total_seconds()),
            )
        if delay_seconds > 900:
            raise ValueError("SQS DelaySeconds cannot exceed 900 seconds")

        self._client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(_job_to_dict(job)),
            DelaySeconds=delay_seconds,
        )

    def consume(self, stage: str, *, max_messages: int = 1) -> Iterator[AbstractContextManager[Job]]:
        """Long-poll SQS and yield one ack/nack context manager per message."""
        queue_url = self._queue_urls.get(stage)
        if queue_url is None:
            raise ValueError(f"Unknown queue stage: {stage}")
        if max_messages < 1 or max_messages > 10:
            raise ValueError("max_messages must be between 1 and 10")

        response = self._client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=self._wait_time,
            VisibilityTimeout=self._visibility_timeout,
        )
        for message in response.get("Messages", []):
            yield self._handle_message(queue_url, message)

    def depth(self, stage: str) -> int:
        """Return SQS's approximate visible plus delayed message count."""
        queue_url = self._queue_urls.get(stage)
        if queue_url is None:
            raise ValueError(f"Unknown queue stage: {stage}")
        response = self._client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesDelayed",
            ],
        )
        attributes = response.get("Attributes", {})
        return sum(
            int(attributes.get(name, 0))
            for name in (
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesDelayed",
            )
        )

    def send_to_dead_letter(self, job: Job, *, reason: str) -> None:
        """Publish a diagnostic copy to the configured dead-letter queue."""
        self._client.send_message(
            QueueUrl=self._dead_letter_url,
            MessageBody=json.dumps({"job": _job_to_dict(job), "reason": reason}),
            MessageAttributes={
                "reason": {"DataType": "String", "StringValue": reason},
            },
        )

    def _handle_message(self, queue_url: str, message: dict[str, Any]) -> AbstractContextManager[Job]:
        receipt_handle = message["ReceiptHandle"]
        job = _job_from_json(message["Body"])
        return _SqsMessageHandle(self._client, queue_url, receipt_handle, job)


class _SqsMessageHandle(AbstractContextManager[Job]):
    def __init__(
        self, client: Any, queue_url: str, receipt_handle: str, job: Job
    ) -> None:
        self._client = client
        self._queue_url = queue_url
        self._receipt_handle = receipt_handle
        self._job = job

    def __enter__(self) -> Job:
        return self._job

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> bool:
        if exception_type is None:
            self._client.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=self._receipt_handle,
            )
        return False


def _job_to_dict(job: Job) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "resource_id": job.resource_id,
        "stage": job.stage,
        "status": job.status.value,
        "attempts": job.attempts,
        "enqueued_at": job.enqueued_at.isoformat(),
        "not_before": job.not_before.isoformat() if job.not_before else None,
    }


def _job_from_json(payload: str) -> Job:
    data = json.loads(payload)
    return Job(
        job_id=data["job_id"],
        resource_id=data["resource_id"],
        stage=data["stage"],
        status=JobStatus(data.get("status", JobStatus.PENDING.value)),
        attempts=data.get("attempts", 0),
        enqueued_at=datetime.fromisoformat(data["enqueued_at"]),
        not_before=(
            datetime.fromisoformat(data["not_before"])
            if data.get("not_before")
            else None
        ),
    )
