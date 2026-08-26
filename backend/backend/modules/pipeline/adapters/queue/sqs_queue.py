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

from collections.abc import Iterator
from contextlib import AbstractContextManager

from ...domain.models import Job
from ...ports.job_queue import JobQueue


class SqsQueue(JobQueue):
    """Queue backed by AWS SQS, one queue URL per stage."""

    def __init__(
        self,
        *,
        queue_urls: dict[str, str],  # stage name -> queue URL
        dead_letter_url: str,
        region: str,
        visibility_timeout: int = 300,
        wait_time_seconds: int = 20,  # long polling — see below
    ) -> None:
        # TODO: one boto3 SQS client, reused.
        self._queue_urls = queue_urls
        self._dead_letter_url = dead_letter_url
        self._visibility_timeout = visibility_timeout
        # 20s is the maximum and the right default: long polling means one API
        # call per 20 seconds of idle instead of one per 100ms. On SQS's
        # per-request pricing, short polling on an idle queue costs real money
        # to receive nothing.
        self._wait_time = wait_time_seconds

    def publish(self, job: Job) -> None:
        """TODO:
        [ ] Serialize the Job to JSON (it is small by design).
        [ ] send_message to the stage's queue URL.
        [ ] For `not_before`, use DelaySeconds (max 900s = 15 min). For
            longer backoffs, publish to a delay queue or store the job with
            a visible_at timestamp — do NOT sleep in the worker.
        [ ] Unknown stage -> PermanentError naming the stage. A typo should
            fail immediately, not publish into the void.
        """
        raise NotImplementedError

    def consume(
        self, stage: str, *, max_messages: int = 1
    ) -> Iterator[AbstractContextManager[Job]]:
        """TODO:
        [ ] receive_message with WaitTimeSeconds=self._wait_time (long poll)
            and MaxNumberOfMessages=max_messages.
        [ ] Yield a context manager per message:
                clean exit -> delete_message (ack)
                exception  -> do NOT delete; let the visibility timeout expire
                              so SQS redelivers, OR call change_message_visibility
                              with the backoff delay to retry sooner.
        [ ] For LONG-RUNNING STAGES (ASR, OCR), extend visibility periodically
            from a heartbeat thread while the job runs. Without it, SQS
            redelivers a job that is still being processed — the duplicate
            transcription problem from the module docstring.
        [ ] Configure a redrive policy on the queue itself so SQS moves
            repeatedly-failing messages to the DLQ automatically. Belt and
            braces alongside our own dead-letter handling.
        """
        raise NotImplementedError

    def depth(self, stage: str) -> int:
        """TODO: get_queue_attributes -> ApproximateNumberOfMessages.

        "Approximate" is fine — it is a trend indicator for the dashboard, not
        an accounting figure. Do not poll it per job; publish it on a timer.
        """
        raise NotImplementedError

    def send_to_dead_letter(self, job: Job, *, reason: str) -> None:
        """TODO: send to the DLQ with the reason and the full traceback in
        message attributes. A DLQ entry with no reason tells the on-call person
        nothing except that something broke.

        ALERT ON DLQ DEPTH > 0 (observability/metrics.py). A dead-letter queue
        nobody watches is just a slower way to lose data.
        """
        raise NotImplementedError
