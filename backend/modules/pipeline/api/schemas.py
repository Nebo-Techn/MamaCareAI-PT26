"""
API request/response schemas (Pydantic).

WHY THESE ARE SEPARATE FROM domain/models.py
It is tempting to return domain objects directly. Don't — they are different
things with different reasons to change:

  - Domain models change when the PIPELINE's rules change.
  - API schemas change when a CLIENT's needs change.

Coupling them means a harmless internal rename becomes a breaking API change,
and an internal field you never meant to expose (last_error with a stack trace,
an object storage key, a reviewer's id) gets serialized to whoever is calling.
The mapping is a few lines of boilerplate and it is worth it.

TODO (junior dev): implement these as pydantic BaseModel classes with real
validation. Validate at the EDGE so nothing invalid reaches a service.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO: implement the following schemas.
#
# --- Submission ---
#
# SubmitRequest
#     source_url: HttpUrl        <- HttpUrl, not str. Pydantic rejects
#                                   malformed and non-http URLs for free.
#     source_type: SourceType | None = None   (inferred when omitted)
#     metadata: dict[str, str] = {}
#     TODO: add a validator rejecting private/loopback hosts (SSRF guard —
#           see services/submission.py). Do it here AND in the service: here
#           for a good error message, there because the service is also
#           reachable from the CLI.
#
# SubmitResponse
#     resource_id: str
#     status: ResourceStatus
#     TODO: return 202 ACCEPTED, not 200. The work has been queued, not done.
#           The status code should tell the truth about what happened.
#
# --- Status ---
#
# ResourceStatusResponse
#     resource_id, source_url, source_type, status
#     detected_language, language_confidence
#     submitted_at, updated_at
#     current_version: int | None
#     error: str | None
#     TODO: NEVER put a raw exception traceback in `error`. Return a short,
#           safe message; the traceback belongs in the logs. Tracebacks leak
#           internal paths and library versions to whoever can call this.
#
# --- Review (PDF 3.6) ---
#
# ReviewPayloadResponse        <- powers the side-by-side view
#     resource_id, title, source_language
#     source_blocks: list[BlockSchema]        LEFT pane
#     translated_units: list[UnitSchema]      RIGHT pane, aligned by `order`
#     machine_units: list[UnitSchema] | None  for diffing after a human edit
#     version_number, engine
#
# EditRequest
#     units: list[UnitSchema]    (order + edited translated_text)
#     note: str | None
#     TODO: validate that `order` values match the existing version's orders
#           exactly. A client sending a block that does not exist, or silently
#           dropping one, would corrupt the alignment the whole review UI and
#           the feedback loop depend on.
#
# DecisionRequest
#     decision: ReviewDecision
#     note: str | None
#     TODO: require a note when decision is NEEDS_EDIT or REJECT. "Rejected,
#           no reason given" is useless to the person who has to act on it, and
#           useless in the audit trail six months later.
# ---------------------------------------------------------------------------
