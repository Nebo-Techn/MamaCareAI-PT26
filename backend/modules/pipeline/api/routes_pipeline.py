"""
Pipeline admin API — submit resources, check status.

    POST /pipeline/resources           submit a URL
    POST /pipeline/resources/upload    submit a PDF file directly
    GET  /pipeline/resources/{id}      status + version history
    GET  /pipeline/resources           list by status (the ops view)
    GET  /pipeline/stats               queue depths, counts per status

NOT A PUBLIC SURFACE. This is an internal tool for the data team. It must sit
behind authentication before it is exposed anywhere — an unauthenticated
endpoint that fetches arbitrary URLs is an open proxy, and someone will find it.
"""

"""
Pipeline admin API — submit resources, check status.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ..container import Container
from ..domain.enums import ResourceStatus
from ..domain.errors import PermanentError
from ..services.submission import SubmissionService
from .schemas import SubmitRequest, SubmitResponse


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def get_container(request: Request) -> Container:
    """Return the application-wide dependency container."""
    container = getattr(request.app.state, "container", None)

    if container is None:
        raise RuntimeError("Pipeline container is not initialized")

    return container


def get_submission_service(
    container: Annotated[Container, Depends(get_container)],
) -> SubmissionService:
    """
    Build a lightweight service around the shared dependencies.

    The container itself remains application-scoped; no database/model
    container is rebuilt per request.
    """
    return SubmissionService(
        resources=container.resources,
        queue=container.queue,
        source_register=getattr(container, "source_register", None),
    )


@router.post(
    "/resources",
    response_model=SubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_resource(
    payload: SubmitRequest,
    service: Annotated[SubmissionService, Depends(get_submission_service)],
) -> SubmitResponse:
    """Submit a URL and enqueue ingestion immediately."""
    if service._source_register is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Source register is not configured",
        )

    try:
        resource = service.submit(
            source_url=str(payload.source_url),
            source_type=payload.source_type,
            submitted_by="system",
            metadata=payload.metadata,
        )
    except PermanentError as exc:
        message = str(exc)

        if "not vetted" in message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    return SubmitResponse(
        resource_id=resource.resource_id,
        status=resource.status,
    )

# TODO (junior dev): create the router and implement the endpoints.
#
#     router = APIRouter(prefix="/pipeline", tags=["pipeline"])
#
#
# POST /resources  ->  202 Accepted, SubmitResponse
#   [ ] Call SubmissionService.submit(). Nothing else.
#   [ ] RETURN IMMEDIATELY — never wait for the fetch. A synchronous fetch
#       here times out on large PDFs, the user retries, and now there are
#       duplicate submissions plus an annoyed user.
#   [ ] Map errors: not vetted -> 400 with a message pointing at
#       data/01_source_register; already submitted -> 200 with the existing id
#       (idempotent, not an error).
#
# POST /resources/upload  ->  202 Accepted
#   [ ] Accept an UploadFile for PDFs submitted by hand.
#   [ ] ENFORCE A MAX SIZE (settings.fetch_max_bytes) while streaming to disk.
#       FastAPI will happily buffer a 2GB upload into memory otherwise.
#   [ ] VERIFY THE MAGIC BYTES (%PDF-), not the filename. A filename is a
#       client-supplied string and means nothing.
#   [ ] Write to object storage and create the resource in FETCHED status,
#       enqueueing "extract" directly. There is nothing to fetch.
#
# GET /resources/{resource_id}  ->  ResourceStatusResponse
#   [ ] Status, timestamps, version count, safe error message.
#   [ ] 404 when unknown.
#
# GET /resources?status=...&limit=&offset=
#   [ ] Paginated. Cap `limit` server-side (say 200) — never let a client
#       request the entire table.
#
# GET /stats
#   [ ] Per-stage queue depth, counts per status, oldest item in review.
#       The 30-second "is it healthy?" view for the team's standup.
#
# DEPENDENCY INJECTION:
#   Use FastAPI `Depends` to get services from the Container built in the app
#   lifespan (see backend/main.py). Do NOT construct a Container per request —
#   that reloads the fastText and MT models on every call.
#
# AUTHENTICATION:
#   [ ] Put every route in this file behind auth before deployment. Start with
#       a shared API key header if that is all there is time for; an open
#       URL-fetching endpoint is a genuine security problem, not a to-do.
