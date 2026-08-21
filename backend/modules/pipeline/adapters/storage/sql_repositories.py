"""
SQLAlchemy repositories — the relational side of PDF 3.5.

ONE FILE, BOTH ENVIRONMENTS. SQLAlchemy speaks SQLite (free MVP) and PostgreSQL
(production), so the MVP exercises the real production code path rather than a
throwaway dev implementation. Only `PIPELINE_DATABASE_URL` changes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    exc,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

# JSON type that uses JSONB on PostgreSQL and fallback JSON on SQLite
JsonType = JSON().with_variant(JSONB(), "postgresql")


# ---------------------------------------------------------------------------
# DOMAIN ENUMS
# ---------------------------------------------------------------------------


class AuthorKind(str, Enum):
    MACHINE = "machine"
    HUMAN = "human"


class ResourceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    FAILED = "failed"


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


# ---------------------------------------------------------------------------
# DOMAIN EXCEPTIONS
# ---------------------------------------------------------------------------


class DomainError(Exception):
    """Base domain exception."""


class DuplicateResourceError(DomainError):
    """Raised when trying to add a duplicate resource."""


class ResourceNotFoundError(DomainError):
    """Raised when a resource is not found."""


class AssignmentNotFoundError(DomainError):
    """Raised when an assignment is not found."""


class InvalidStateTransitionError(DomainError):
    """Raised when an invalid state transition is attempted."""


class UnauthorizedAssignmentAccessError(DomainError):
    """Raised when trying to access an assignment without authorization."""


# ---------------------------------------------------------------------------
# DOMAIN MODELS
# ---------------------------------------------------------------------------


class Resource:
    """Domain model for a resource."""

    def __init__(
        self,
        resource_id: str,
        source_type: str,
        source_url: str,
        status: ResourceStatus,
        content_hash: str,
        submitted_at: datetime,
        updated_at: datetime,
        attempt_count: int = 0,
        last_error: str | None = None,
        raw_object_key: str | None = None,
        detected_language: str | None = None,
        language_confidence: float | None = None,
        source_metadata: dict | None = None,
        version: int = 1,
    ):

        self.resource_id = resource_id
        self.source_type = source_type
        self.source_url = source_url
        self.status = status
        self.content_hash = content_hash
        self.submitted_at = submitted_at
        self.updated_at = updated_at
        self.attempt_count = attempt_count
        self.last_error = last_error
        self.raw_object_key = raw_object_key
        self.detected_language = detected_language
        self.language_confidence = language_confidence
        self.source_metadata = source_metadata or {}
        self.version = version


class TextBlock:
    """Domain model for a text block."""

    def __init__(
        self,
        text: str,
        block_id: str | None = None,
        order: int = 0,
        page: str | None = None,
        bbox: str | None = None,
        **kwargs,
    ):
        self.text = text
        self.block_id = block_id
        self.order = order
        self.page = page
        self.bbox = bbox or {}


class NormalizedDocument:
    """Domain model for a normalized document."""

    def __init__(
        self,
        resource_id: str,
        blocks: list[TextBlock],
        title: str | None = None,
        author: str | None = None,
        published_date: str | None = None,
        source_metadata: str | None = None,
    ):
        self.resource_id = resource_id
        self.title = title
        self.author = author
        self.published_date = published_date
        self.blocks = blocks or []
        self.source_metadata = source_metadata or {}


class TranslationUnit:
    """Domain model for a translation unit."""

    def __init__(
        self,
        source_text: str,
        target_text: str | None = None,
        unit_id: str | None = None,
        **kwargs,
    ):
        self.unit_id = unit_id
        self.source_text = source_text
        self.target_text = target_text


class ContentVersion:
    """Domain model for a content version."""

    def __init__(
        self,
        version_id: str,
        resource_id: str,
        version_number: int,
        author_kind: AuthorKind,
        author_id: str,
        created_at: datetime,
        units: list[TranslationUnit],
        engine: str | None = None,
        note: str | None = None,
    ):
        self.version_id = version_id
        self.resource_id = resource_id
        self.version_number = version_number
        self.author_kind = author_kind
        self.author_id = author_id
        self.engine = engine
        self.note = note
        self.created_at = created_at
        self.units = units or []


class ReviewAssignment:
    """Domain model for a review assignment."""

    def __init__(
        self,
        assignment_id: str,
        resource_id: str,
        assigned_at: datetime,
        reviewer_id: str | None = None,
        decision: str | None = None,
        priority: int = 0,
        completed_at: str | None = None,
    ):
        self.assignment_id = assignment_id
        self.resource_id = resource_id
        self.reviewer_id = reviewer_id
        self.decision = decision
        self.priority = priority
        self.assigned_at = assigned_at
        self.completed_at = completed_at


class AuditEvent:
    """Domain model for an audit event."""

    def __init__(
        self,
        event_id: str,
        resource_id: str,
        actor_id: str,
        action: str,
        to_status: ResourceStatus,
        at: datetime,
        from_status: str | None = None,
        details: str | None = None,
    ):
        self.event_id = event_id
        self.resource_id = resource_id
        self.actor_id = actor_id
        self.action = action
        self.from_status = from_status
        self.to_status = to_status
        self.at = at
        self.details = details or {}


# ---------------------------------------------------------------------------
# PORT INTERFACES
# ---------------------------------------------------------------------------


class ResourceRepository:
    """Interface for resource repository."""


class DocumentRepository:
    """Interface for document repository."""


class VersionRepository:
    """Interface for version repository."""


class ReviewRepository:
    """Interface for review repository."""


# ---------------------------------------------------------------------------
# ORM TABLE DEFINITIONS
# ---------------------------------------------------------------------------


class ResourceORM(Base):
    __tablename__ = "resources"

    resource_id = Column(String, primary_key=True)
    source_type = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    status = Column(String, nullable=False)
    content_hash = Column(String, nullable=False, unique=True)
    submitted_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    raw_object_key = Column(String, nullable=True)
    detected_language = Column(String, nullable=True)
    language_confidence = Column(Float, nullable=True)
    source_metadata = Column(JsonType, nullable=True)
    version = Column(Integer, default=1, nullable=False)

    __table_args__ = (Index("idx_resources_status_updated_at", "status", "updated_at"),)


class DocumentORM(Base):
    __tablename__ = "documents"

    resource_id = Column(String, ForeignKey("resources.resource_id"), primary_key=True)
    title = Column(Text, nullable=True)
    author = Column(Text, nullable=True)
    published_date = Column(DateTime, nullable=True)
    blocks = Column(JsonType, nullable=False)  # List[TextBlock]
    source_metadata = Column(JsonType, nullable=True)


class ContentVersionORM(Base):
    __tablename__ = "content_versions"

    version_id = Column(String, primary_key=True)
    resource_id = Column(
        String, ForeignKey("resources.resource_id"), nullable=False, index=True
    )
    version_number = Column(Integer, nullable=False)
    author_kind = Column(String, nullable=False)
    author_id = Column(String, nullable=False)
    engine = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    units = Column(JsonType, nullable=False)  # List[TranslationUnit]

    __table_args__ = (
        UniqueConstraint(
            "resource_id", "version_number", name="uq_resource_version_number"
        ),
    )


class ReviewAssignmentORM(Base):
    __tablename__ = "review_assignments"

    assignment_id = Column(String, primary_key=True)
    resource_id = Column(
        String, ForeignKey("resources.resource_id"), nullable=False, index=True
    )
    reviewer_id = Column(String, nullable=True)
    decision = Column(String, nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    assigned_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_review_claim", "reviewer_id", "completed_at", text("priority DESC")),
    )


class AuditEventORM(Base):
    __tablename__ = "audit_events"

    event_id = Column(String, primary_key=True)
    resource_id = Column(
        String, ForeignKey("resources.resource_id"), nullable=False, index=True
    )
    actor_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    at = Column(DateTime, nullable=False)
    details = Column(JsonType, nullable=True)


# ---------------------------------------------------------------------------
# REPOSITORY IMPLEMENTATIONS
# ---------------------------------------------------------------------------


class SqlResourceRepository(ResourceRepository):
    """Resource state in a relational database."""

    def __init__(self, *, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def add(self, resource: Resource) -> None:
        session: Session = self._session_factory()
        try:
            row = ResourceORM(
                resource_id=resource.resource_id,
                source_type=resource.source_type,
                source_url=resource.source_url,
                status=resource.status.value,
                content_hash=resource.content_hash,
                submitted_at=resource.submitted_at,
                updated_at=resource.updated_at,
                attempt_count=resource.attempt_count,
                last_error=resource.last_error,
                raw_object_key=resource.raw_object_key,
                detected_language=resource.detected_language,
                language_confidence=resource.language_confidence,
                source_metadata=resource.source_metadata,
                version=getattr(resource, "version", 1),
            )
            session.add(row)
            session.commit()
        except exc.IntegrityError as e:
            session.rollback()
            raise DuplicateResourceError(
                f"Resource with content_hash '{resource.content_hash}' already exists."
            ) from e
        finally:
            session.close()

    def get(self, resource_id: str) -> Resource:
        session: Session = self._session_factory()
        try:
            row = session.get(ResourceORM, resource_id)
            if not row:
                raise ResourceNotFoundError(f"Resource '{resource_id}' not found.")
            return Resource(
                resource_id=row.resource_id,
                source_type=row.source_type,
                source_url=row.source_url,
                status=ResourceStatus(row.status),
                content_hash=row.content_hash,
                submitted_at=row.submitted_at,
                updated_at=row.updated_at,
                attempt_count=row.attempt_count,
                last_error=row.last_error,
                raw_object_key=row.raw_object_key,
                detected_language=row.detected_language,
                language_confidence=row.language_confidence,
                source_metadata=row.source_metadata,
                version=row.version,
            )
        finally:
            session.close()

    def find_by_content_hash(self, content_hash: str) -> Resource | None:
        session: Session = self._session_factory()
        try:
            stmt = select(ResourceORM).where(ResourceORM.content_hash == content_hash)
            row = session.execute(stmt).scalar_one_or_none()
            if not row:
                return None
            return Resource(
                resource_id=row.resource_id,
                source_type=row.source_type,
                source_url=row.source_url,
                status=ResourceStatus(row.status),
                content_hash=row.content_hash,
                submitted_at=row.submitted_at,
                updated_at=row.updated_at,
                attempt_count=row.attempt_count,
                last_error=row.last_error,
                raw_object_key=row.raw_object_key,
                detected_language=row.detected_language,
                language_confidence=row.language_confidence,
                source_metadata=row.source_metadata,
                version=row.version,
            )
        finally:
            session.close()

    def save(self, resource: Resource) -> None:
        """Conditional update on version to prevent lost updates under concurrency."""
        session: Session = self._session_factory()
        try:
            old_version = getattr(resource, "version", 1)
            stmt = (
                update(ResourceORM)
                .where(
                    ResourceORM.resource_id == resource.resource_id,
                    ResourceORM.version == old_version,
                )
                .values(
                    source_type=resource.source_type,
                    source_url=resource.source_url,
                    status=resource.status.value,
                    content_hash=resource.content_hash,
                    submitted_at=resource.submitted_at,
                    updated_at=resource.updated_at,
                    attempt_count=resource.attempt_count,
                    last_error=resource.last_error,
                    raw_object_key=resource.raw_object_key,
                    detected_language=resource.detected_language,
                    language_confidence=resource.language_confidence,
                    source_metadata=resource.source_metadata,
                    version=old_version + 1,
                )
            )
            result = session.execute(stmt)
            session.commit()

            if result.rowcount == 0:
                raise InvalidStateTransitionError(
                    f"Concurrent modification detected for resource '{resource.resource_id}'. "
                    f"Expected version {old_version}."
                )
        finally:
            session.close()

    def list_by_status(
        self, status: ResourceStatus, *, limit: int = 100, offset: int = 0
    ) -> list[Resource]:
        limit = min(limit, 500)  # Sane max limit
        session: Session = self._session_factory()
        try:
            stmt = (
                select(ResourceORM)
                .where(ResourceORM.status == status.value)
                .order_by(ResourceORM.updated_at.asc())
                .offset(offset)
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
            return [
                Resource(
                    resource_id=row.resource_id,
                    source_type=row.source_type,
                    source_url=row.source_url,
                    status=ResourceStatus(row.status),
                    content_hash=row.content_hash,
                    submitted_at=row.submitted_at,
                    updated_at=row.updated_at,
                    attempt_count=row.attempt_count,
                    last_error=row.last_error,
                    raw_object_key=row.raw_object_key,
                    detected_language=row.detected_language,
                    language_confidence=row.language_confidence,
                    source_metadata=row.source_metadata,
                    version=row.version,
                )
                for row in rows
            ]
        finally:
            session.close()


class SqlDocumentRepository(DocumentRepository):
    """Normalized documents in a relational database."""

    def __init__(self, *, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def save_document(self, document: NormalizedDocument) -> None:
        session: Session = self._session_factory()
        try:
            blocks_data = [
                b.__dict__ if hasattr(b, "__dict__") else b for b in document.blocks
            ]
            existing = session.get(DocumentORM, document.resource_id)
            if existing:
                existing.title = document.title
                existing.author = document.author
                existing.published_date = document.published_date
                existing.blocks = blocks_data
                existing.source_metadata = document.source_metadata
            else:
                row = DocumentORM(
                    resource_id=document.resource_id,
                    title=document.title,
                    author=document.author,
                    published_date=document.published_date,
                    blocks=blocks_data,
                    source_metadata=document.source_metadata,
                )
                session.add(row)
            session.commit()
        finally:
            session.close()

    def get_document(self, resource_id: str) -> NormalizedDocument:
        session: Session = self._session_factory()
        try:
            row = session.get(DocumentORM, resource_id)
            if not row:
                raise ResourceNotFoundError(
                    f"Document for resource '{resource_id}' not found."
                )

            raw_blocks = row.blocks or []
            blocks = [TextBlock(**b) if isinstance(b, dict) else b for b in raw_blocks]
            blocks.sort(key=lambda b: getattr(b, "order", 0))

            return NormalizedDocument(
                resource_id=row.resource_id,
                title=row.title,
                author=row.author,
                published_date=row.published_date,
                blocks=blocks,
                source_metadata=row.source_metadata,
            )
        finally:
            session.close()


class SqlVersionRepository(VersionRepository):
    """Append-only content versions."""

    def __init__(self, *, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def save_version(self, version: ContentVersion) -> None:
        session: Session = self._session_factory()
        try:
            # Atomically compute the next version_number inside transaction
            stmt = select(
                func.coalesce(func.max(ContentVersionORM.version_number), 0)
            ).where(ContentVersionORM.resource_id == version.resource_id)

            # Use row locking if supported (PostgreSQL)
            if session.bind and session.bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update()

            current_max = session.execute(stmt).scalar() or 0
            next_version = current_max + 1

            units_data = [
                u.__dict__ if hasattr(u, "__dict__") else u for u in version.units
            ]

            row = ContentVersionORM(
                version_id=version.version_id,
                resource_id=version.resource_id,
                version_number=next_version,
                author_kind=version.author_kind.value
                if isinstance(version.author_kind, AuthorKind)
                else version.author_kind,
                author_id=version.author_id,
                engine=version.engine,
                note=version.note,
                created_at=version.created_at,
                units=units_data,
            )
            session.add(row)
            session.commit()
        except exc.IntegrityError as e:
            session.rollback()
            raise DuplicateResourceError(
                "Version number collision on concurrent write."
            ) from e
        finally:
            session.close()

    def get_latest(self, resource_id: str) -> ContentVersion | None:
        session: Session = self._session_factory()
        try:
            stmt = (
                select(ContentVersionORM)
                .where(ContentVersionORM.resource_id == resource_id)
                .order_by(ContentVersionORM.version_number.desc())
                .limit(1)
            )
            row = session.execute(stmt).scalar_one_or_none()
            return self._to_domain(row) if row else None
        finally:
            session.close()

    def get_machine_version(self, resource_id: str) -> ContentVersion | None:
        session: Session = self._session_factory()
        try:
            stmt = (
                select(ContentVersionORM)
                .where(
                    ContentVersionORM.resource_id == resource_id,
                    ContentVersionORM.author_kind == AuthorKind.MACHINE.value,
                )
                .order_by(ContentVersionORM.version_number.asc())
                .limit(1)
            )
            row = session.execute(stmt).scalar_one_or_none()
            return self._to_domain(row) if row else None
        finally:
            session.close()

    def list_versions(self, resource_id: str) -> list[ContentVersion]:
        session: Session = self._session_factory()
        try:
            stmt = (
                select(ContentVersionORM)
                .where(ContentVersionORM.resource_id == resource_id)
                .order_by(ContentVersionORM.version_number.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_domain(row) for row in rows]
        finally:
            session.close()

    def _to_domain(self, row: ContentVersionORM) -> ContentVersion:
        raw_units = row.units or []
        units = [TranslationUnit(**u) if isinstance(u, dict) else u for u in raw_units]
        return ContentVersion(
            version_id=row.version_id,
            resource_id=row.resource_id,
            version_number=row.version_number,
            author_kind=AuthorKind(row.author_kind),
            author_id=row.author_id,
            engine=row.engine,
            note=row.note,
            created_at=row.created_at,
            units=units,
        )


class SqlReviewRepository(ReviewRepository):
    """Review assignments and audit trail."""

    def __init__(self, *, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create_assignment(self, assignment: ReviewAssignment) -> None:
        session: Session = self._session_factory()
        try:
            existing = session.execute(
                select(ReviewAssignmentORM).where(
                    ReviewAssignmentORM.resource_id == assignment.resource_id,
                    ReviewAssignmentORM.completed_at.is_(None),
                )
            ).scalar_one_or_none()
            if existing:
                raise DuplicateResourceError(
                    f"Open assignment already exists for resource '{assignment.resource_id}'."
                )

            row = ReviewAssignmentORM(
                assignment_id=assignment.assignment_id,
                resource_id=assignment.resource_id,
                reviewer_id=assignment.reviewer_id,
                decision=assignment.decision.value if assignment.decision else None,
                priority=assignment.priority,
                assigned_at=assignment.assigned_at,
                completed_at=assignment.completed_at,
            )
            session.add(row)
            session.commit()
        finally:
            session.close()

    def get_assignment(self, assignment_id: str) -> ReviewAssignment:
        session: Session = self._session_factory()
        try:
            row = session.get(ReviewAssignmentORM, assignment_id)
            if not row:
                raise AssignmentNotFoundError(
                    f"Assignment '{assignment_id}' not found."
                )
            return self._to_domain_assignment(row)
        finally:
            session.close()

    def claim_next(self, reviewer_id: str) -> ReviewAssignment | None:
        """Atomically claims next open review assignment."""
        session: Session = self._session_factory()
        try:
            dialect_name = session.bind.dialect.name if session.bind else ""

            if dialect_name == "postgresql":
                stmt = (
                    select(ReviewAssignmentORM)
                    .where(
                        ReviewAssignmentORM.reviewer_id.is_(None),
                        ReviewAssignmentORM.completed_at.is_(None),
                    )
                    .order_by(
                        ReviewAssignmentORM.priority.desc(),
                        ReviewAssignmentORM.assigned_at.asc(),
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                row = session.execute(stmt).scalar_one_or_none()
                if not row:
                    return None

                row.reviewer_id = reviewer_id
                session.commit()
                return self._to_domain_assignment(row)

            else:
                # SQLite fallback strategy via optimistic update retry loop
                stmt = (
                    select(ReviewAssignmentORM.assignment_id)
                    .where(
                        ReviewAssignmentORM.reviewer_id.is_(None),
                        ReviewAssignmentORM.completed_at.is_(None),
                    )
                    .order_by(
                        ReviewAssignmentORM.priority.desc(),
                        ReviewAssignmentORM.assigned_at.asc(),
                    )
                )
                candidate_ids = session.execute(stmt).scalars().all()

                for assign_id in candidate_ids:
                    update_stmt = (
                        update(ReviewAssignmentORM)
                        .where(
                            ReviewAssignmentORM.assignment_id == assign_id,
                            ReviewAssignmentORM.reviewer_id.is_(None),
                        )
                        .values(reviewer_id=reviewer_id)
                    )
                    res = session.execute(update_stmt)
                    session.commit()

                    if res.rowcount > 0:
                        row = session.get(ReviewAssignmentORM, assign_id)
                        return self._to_domain_assignment(row)

                return None
        finally:
            session.close()

    def save_assignment(self, assignment: ReviewAssignment) -> None:
        session: Session = self._session_factory()
        try:
            row = session.get(ReviewAssignmentORM, assignment.assignment_id)
            if not row:
                raise AssignmentNotFoundError(
                    f"Assignment '{assignment.assignment_id}' not found."
                )

            if row.reviewer_id != assignment.reviewer_id:
                raise UnauthorizedAssignmentAccessError(
                    "Cannot modify an assignment assigned to another reviewer."
                )

            row.decision = assignment.decision.value if assignment.decision else None
            row.completed_at = assignment.completed_at
            session.commit()
        finally:
            session.close()

    def append_audit(self, event: AuditEvent) -> None:
        session: Session = self._session_factory()
        try:
            row = AuditEventORM(
                event_id=event.event_id,
                resource_id=event.resource_id,
                actor_id=event.actor_id,
                action=event.action,
                from_status=event.from_status.value if event.from_status else None,
                to_status=event.to_status.value
                if isinstance(event.to_status, ResourceStatus)
                else event.to_status,
                at=event.at,
                details=event.details,
            )
            session.add(row)
            session.commit()
        finally:
            session.close()

    def list_audit(self, resource_id: str) -> list[AuditEvent]:
        session: Session = self._session_factory()
        try:
            stmt = (
                select(AuditEventORM)
                .where(AuditEventORM.resource_id == resource_id)
                .order_by(AuditEventORM.at.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [
                AuditEvent(
                    event_id=row.event_id,
                    resource_id=row.resource_id,
                    actor_id=row.actor_id,
                    action=row.action,
                    from_status=ResourceStatus(row.from_status)
                    if row.from_status
                    else None,
                    to_status=ResourceStatus(row.to_status),
                    at=row.at,
                    details=row.details,
                )
                for row in rows
            ]
        finally:
            session.close()

    def _to_domain_assignment(self, row: ReviewAssignmentORM) -> ReviewAssignment:
        return ReviewAssignment(
            assignment_id=row.assignment_id,
            resource_id=row.resource_id,
            reviewer_id=row.reviewer_id,
            decision=ReviewDecision(row.decision) if row.decision else None,
            priority=row.priority,
            assigned_at=row.assigned_at,
            completed_at=row.completed_at,
        )
