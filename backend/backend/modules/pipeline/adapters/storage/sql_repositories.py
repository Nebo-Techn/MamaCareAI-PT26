"""
SQLAlchemy repositories — the relational side of PDF 3.5.

ONE FILE, BOTH ENVIRONMENTS. SQLAlchemy speaks SQLite (free MVP) and PostgreSQL
(production), so the MVP exercises the real production code path rather than a
throwaway dev implementation. Only `PIPELINE_DATABASE_URL` changes.

THE TWO THINGS THAT MUST BE RIGHT IN THIS FILE
Everything else here is ordinary CRUD. These two are what keep a distributed
pipeline correct, and both are easy to write incorrectly in a way that only
fails under concurrency — that is, in production, not in your tests:

  1. `save()` MUST be a CONDITIONAL update (compare-and-set on status).
  2. `claim_next()` MUST be atomic (SELECT ... FOR UPDATE SKIP LOCKED).

Get these wrong and you get double-processing and two reviewers editing the
same document. Write a concurrency test for both — spawn two threads, assert
exactly one wins.

TRANSLATION BOUNDARY: this file maps ORM rows to domain objects and back.
Domain objects must NEVER leak out with a live session attached; return plain
frozen dataclasses so a stage cannot accidentally trigger lazy loads or hold a
connection open.
"""

from __future__ import annotations

from ...domain.enums import ResourceStatus
from ...domain.models import (
    AuditEvent,
    ContentVersion,
    NormalizedDocument,
    Resource,
    ReviewAssignment,
)
from ...ports.repositories import (
    DocumentRepository,
    ResourceRepository,
    ReviewRepository,
    VersionRepository,
)

# ---------------------------------------------------------------------------
# TODO (junior dev): define the ORM tables in this section.
#
# TABLES AND THE INDEXES THAT MAKE THEM WORK:
#
#   resources
#     resource_id      PK
#     source_type, source_url, status, content_hash
#     submitted_at, updated_at, attempt_count, last_error
#     raw_object_key, detected_language, language_confidence
#     source_metadata  JSON
#     -- UNIQUE INDEX on content_hash  <- THIS is what makes dedup hold under
#        concurrency. The Deduplicator port is only a fast pre-check; this
#        constraint is the actual guarantee.
#     -- INDEX on (status, updated_at)  <- every queue/dashboard query filters
#        by status and orders by time. Without it, those pages table-scan and
#        get slower every week until someone notices in month three.
#
#   documents
#     resource_id      PK/FK
#     title, author, published_date
#     blocks           JSON (list of TextBlock)
#     source_metadata  JSON
#
#   content_versions
#     version_id       PK
#     resource_id      FK, INDEXED
#     version_number   int
#     author_kind, author_id, engine, note, created_at
#     units            JSON (list of TranslationUnit)
#     -- UNIQUE (resource_id, version_number)  <- prevents two concurrent
#        reviewers both creating "version 3"
#     -- NO UPDATE PATH. Insert only. See ports/repositories.py.
#
#   review_assignments
#     assignment_id    PK
#     resource_id      FK, INDEXED
#     reviewer_id      NULLABLE (null = unclaimed)
#     decision, priority, assigned_at, completed_at
#     -- INDEX on (reviewer_id, completed_at, priority DESC) for claim_next
#
#   audit_events
#     event_id         PK
#     resource_id      FK, INDEXED
#     actor_id, action, from_status, to_status, at, details JSON
#     -- APPEND ONLY. No update, no delete, ever.
#
# JSON COLUMNS: use JSONB on PostgreSQL (indexable, binary) and JSON on SQLite.
# SQLAlchemy's JSON type with a postgresql variant handles both.
# ---------------------------------------------------------------------------


class SqlResourceRepository(ResourceRepository):
    """Resource state in a relational database."""

    def __init__(self, *, session_factory: object) -> None:
        # A FACTORY, not a session. Each operation opens its own short
        # transaction. A long-lived session shared across jobs holds locks and
        # accumulates stale identity-map state — a classic source of
        # "why is this row not updating?" confusion.
        self._session_factory = session_factory

    def add(self, resource: Resource) -> None:
        """TODO: insert. Let the UNIQUE constraint on content_hash raise on a
        duplicate; catch IntegrityError and convert it to a clear domain error
        rather than surfacing a raw database exception to a stage."""
        raise NotImplementedError

    def get(self, resource_id: str) -> Resource:
        """TODO: select by PK, map row -> Resource, PermanentError if missing."""
        raise NotImplementedError

    def find_by_content_hash(self, content_hash: str) -> Resource | None:
        """TODO: select by the indexed content_hash column. None if absent."""
        raise NotImplementedError

    def save(self, resource: Resource) -> None:
        """THE MOST IMPORTANT METHOD IN THIS FILE. Conditional update only.

        TODO (junior dev):
          [ ] The caller passes an already-transitioned Resource, so you need
              the EXPECTED PRIOR STATUS to compare against. Simplest correct
              approach: add a `version` integer column to `resources`, bump it
              on every save, and write

                  UPDATE resources SET ..., version = :old_version + 1
                  WHERE resource_id = :id AND version = :old_version

          [ ] If rowcount == 0, another worker modified this resource first.
              Raise InvalidStateTransition. The base stage catches it, logs,
              and stops — the other worker's write wins, which is correct.

          [ ] NEVER write a blind `UPDATE ... WHERE resource_id = :id`. It
              works perfectly in every single-threaded test and silently
              double-processes resources the moment you run two workers.
        """
        raise NotImplementedError

    def list_by_status(
        self, status: ResourceStatus, *, limit: int = 100, offset: int = 0
    ) -> list[Resource]:
        """TODO: filtered, ordered by updated_at, ALWAYS paginated. Cap `limit`
        at a sane maximum so a caller cannot request the whole table."""
        raise NotImplementedError


class SqlDocumentRepository(DocumentRepository):
    """Normalized documents in a relational database."""

    def save_document(self, document: NormalizedDocument) -> None:
        """TODO: upsert by resource_id (ON CONFLICT DO UPDATE). Upsert is what
        makes re-extraction idempotent — keep it that way."""
        raise NotImplementedError

    def get_document(self, resource_id: str) -> NormalizedDocument:
        """TODO: select and rehydrate blocks from JSON into TextBlock objects,
        sorted by `order`. Never trust stored order to be the sort order."""
        raise NotImplementedError


class SqlVersionRepository(VersionRepository):
    """Append-only content versions."""

    def save_version(self, version: ContentVersion) -> None:
        """TODO:
        [ ] INSERT ONLY. There is deliberately no update method on the port.
        [ ] Assign version_number INSIDE the transaction:
                SELECT COALESCE(MAX(version_number), 0) + 1
                FROM content_versions WHERE resource_id = :id
            with the rows locked (SELECT ... FOR UPDATE). Computing it in
            Python beforehand gives two concurrent reviewers the same number,
            and the UNIQUE constraint then rejects one of their edits —
            losing a reviewer's work, which is unacceptable.
        """
        raise NotImplementedError

    def get_latest(self, resource_id: str) -> ContentVersion | None:
        """TODO: highest version_number for the resource. This is what gets
        published — it is the human edit when one exists."""
        raise NotImplementedError

    def get_machine_version(self, resource_id: str) -> ContentVersion | None:
        """TODO: author_kind = MACHINE, lowest version_number. The diff baseline."""
        raise NotImplementedError

    def list_versions(self, resource_id: str) -> list[ContentVersion]:
        """TODO: all versions, ordered by version_number ascending."""
        raise NotImplementedError


class SqlReviewRepository(ReviewRepository):
    """Review assignments and audit trail."""

    def create_assignment(self, assignment: ReviewAssignment) -> None:
        """TODO: insert. Guard against creating a second OPEN assignment for a
        resource that already has one."""
        raise NotImplementedError

    def get_assignment(self, assignment_id: str) -> ReviewAssignment:
        """TODO: select by PK; PermanentError if missing."""
        raise NotImplementedError

    def claim_next(self, reviewer_id: str) -> ReviewAssignment | None:
        """THE SECOND CRITICAL METHOD. Must be atomic.

        TODO (junior dev):
          [ ] PostgreSQL:
                  SELECT ... WHERE reviewer_id IS NULL AND completed_at IS NULL
                  ORDER BY priority DESC, assigned_at ASC
                  LIMIT 1 FOR UPDATE SKIP LOCKED
              then UPDATE that row's reviewer_id, all in ONE transaction.
              SKIP LOCKED is the key: two reviewers clicking "next" at the same
              moment get DIFFERENT rows instead of blocking or colliding.

          [ ] SQLite has no SKIP LOCKED. Use a conditional update instead:
                  UPDATE ... SET reviewer_id = :me
                  WHERE assignment_id = :id AND reviewer_id IS NULL
              and re-try the selection if rowcount == 0. Correct, if less
              elegant — and fine at MVP reviewer volume.

          [ ] Return None when the queue is empty. That is a normal state, not
              an error — do not raise, and do not log it as a problem.
        """
        raise NotImplementedError

    def save_assignment(self, assignment: ReviewAssignment) -> None:
        """TODO: update decision/completed_at. Verify the reviewer_id matches
        the one on the row — a reviewer must not be able to complete someone
        else's assignment."""
        raise NotImplementedError

    def append_audit(self, event: AuditEvent) -> None:
        """TODO: plain insert. Never expose update or delete for this table.
        If the audit trail is editable, it is not an audit trail."""
        raise NotImplementedError

    def list_audit(self, resource_id: str) -> list[AuditEvent]:
        """TODO: all events for a resource, ordered by `at` ascending."""
        raise NotImplementedError
