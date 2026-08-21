"""
Submission service — the front door of the pipeline.

Accepts a URL, validates it, creates the Resource record, and enqueues the
first job. Returns IMMEDIATELY with a resource_id.

WHY IT RETURNS IMMEDIATELY
"Every source type becomes a job on a queue, not a synchronous call." A
submission endpoint that waits for a 40MB PDF to download will time out, and
the user will click submit again, and now you have duplicate work plus an
angry user. Accept, enqueue, return an id they can poll.

MAMACARE-SPECIFIC GATE (ARCHITECTURE.md non-negotiable #4):
Nothing enters this pipeline that is not already vetted in
`data/01_source_register`. This service is where that is enforced. Do not add a
"just this once" bypass — an unvetted source that reaches the knowledge base
breaks the traceability guarantee the whole project rests on.
"""

from __future__ import annotations

from ..domain.enums import SourceType
from ..domain.models import Resource
from ..ports.job_queue import JobQueue
from ..ports.repositories import ResourceRepository


class SubmissionService:
    """Creates resources and starts them down the pipeline."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        source_register: object,  # TODO: type once the register reader exists
    ) -> None:
        self._resources = resources
        self._queue = queue
        self._source_register = source_register

    def submit(
        self,
        *,
        source_url: str,
        source_type: SourceType | None = None,
        submitted_by: str,
        metadata: dict[str, object] | None = None,
    ) -> Resource:
        """Accept a resource for processing and return its record.

        TODO (junior dev) — implement in this order:

          1. VALIDATE THE URL:
             http/https only. Reject file://, ftp://, and anything resolving to
             a private/loopback address. This is an SSRF guard: an endpoint that
             fetches arbitrary URLs from user input can be pointed at internal
             services. Not paranoia — it is the standard attack on any
             URL-ingesting system, and we are building exactly that.

          2. VETTING GATE:
                 if not self._source_register.is_approved(source_url):
                     raise PermanentError("source not vetted; add it to "
                                          "data/01_source_register first")

          3. INFER source_type when not given (URL/extension/platform sniffing),
             but let an explicit argument win — the caller may know better than
             the heuristic.

          4. CHEAP DEDUP CHECK: if a resource with the same URL is already
             in-flight or published, return the EXISTING record rather than
             creating a second one. Two identical rows is a data problem you
             will be untangling by hand later.

          5. CREATE + ENQUEUE, in that order:
                 resource = Resource(resource_id=str(uuid4()), status=SUBMITTED, ...)
                 self._resources.add(resource)      # commit FIRST
                 self._queue.publish(Job(..., stage="ingest"))   # then enqueue
             Order matters: enqueueing first means a fast worker can pick up the
             job before the row exists and fail with "resource not found".

          6. RETURN the resource so the caller gets the id to poll.

        BATCH SUBMISSION: add `submit_many` when the team starts loading the
        source register in bulk. Do NOT loop over `submit` in a route handler —
        one slow validation in a 500-item batch times out the whole request.
        """
        raise NotImplementedError
