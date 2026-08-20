"""
Review API (PDF 3.6) — the backend for the human review UI.

    GET  /review/next                     claim the next item
    GET  /review/{resource_id}            side-by-side payload
    POST /review/{assignment_id}/edit     save corrections as a new version
    POST /review/{assignment_id}/decision approve / needs_edit / reject
    GET  /review/{resource_id}/versions   version history
    GET  /review/{resource_id}/audit      who did what, when
    POST /review/{resource_id}/language   confirm a low-confidence language

Every handler is a thin wrapper over `ReviewService`. The workflow rules live
there so they are testable without HTTP and cannot be bypassed by a second
client.

PDF 5 suggests a React app or an adapted Label Studio for the UI itself. Either
way it talks to these endpoints — which is exactly why the workflow does not
live in the frontend. A rule enforced in JavaScript is a suggestion.
"""

from __future__ import annotations

# TODO (junior dev): create the router and implement the endpoints.
#
#     router = APIRouter(prefix="/review", tags=["review"])
#
#
# GET /next  ->  ReviewPayloadResponse | 204 No Content
#   [ ] ReviewService.claim_next(reviewer_id from the auth context).
#   [ ] 204 when the queue is empty — a normal state, not an error.
#   [ ] The reviewer_id comes from AUTH, never from a query parameter. A
#       client-supplied reviewer id makes the entire audit trail worthless.
#
# GET /{resource_id}  ->  ReviewPayloadResponse
#   [ ] ReviewService.get_review_payload().
#   [ ] Returns source blocks and translated units ALIGNED BY `order` — the
#       side-by-side view. Align on the server, not in the frontend, so the
#       rule exists once and is tested.
#
# POST /{assignment_id}/edit  ->  201 Created
#   [ ] ReviewService.submit_edit(). Creates a NEW VERSION; never an update.
#   [ ] 403 if the caller does not own the assignment.
#   [ ] 201 with the new version number — it created a resource.
#
# POST /{assignment_id}/decision  ->  200 OK
#   [ ] ReviewService.submit_decision().
#   [ ] APPROVE is the governance-critical action: it makes this content
#       authoritative and queues publication. Require the reviewer role, and
#       check it in the SERVICE as well as here.
#   [ ] Require a note for NEEDS_EDIT and REJECT.
#
# GET /{resource_id}/versions  ->  list[VersionSummary]
#   [ ] Full history: who, when, which engine, machine vs human. Shows the
#       reviewer that their edits are preserved rather than overwriting the MT.
#
# GET /{resource_id}/audit  ->  list[AuditEventSchema]
#   [ ] The governance trail. Read-only, always.
#
# POST /{resource_id}/language  ->  200 OK
#   [ ] Confirm the language for a NEEDS_LANGUAGE_CONFIRMATION resource
#       (PDF 3.3), then re-enqueue "detect_language". The stage sees the
#       human-confirmed language, trusts it, and continues.
#   [ ] Record WHO confirmed it in the audit trail — the stage checks for that
#       marker so it never overwrites a human decision with a model guess.
#
# --- Cross-cutting for this router ---
#
# ROLES AND PERMISSIONS (PDF 3.6, Governance):
#   [ ] Reviewer  : claim, edit, request changes
#   [ ] Approver  : everything above, plus approve/publish
#   [ ] Read-only : view payloads, versions, and audit
#   Enforce in the service layer. Route-level checks are for good error
#   messages; the service check is the actual rule.
#
# PERFORMANCE:
#   [ ] The payload endpoint is called on every item a reviewer opens. Keep it
#       to a small number of queries — an N+1 over versions will make the
#       review UI feel slow, and reviewer throughput is the pipeline's real
#       bottleneck.
