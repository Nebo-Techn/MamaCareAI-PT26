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

from __future__ import annotations

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
