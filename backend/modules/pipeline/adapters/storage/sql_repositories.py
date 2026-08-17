from __future__ import annotations
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey, UniqueConstraint, Index, func, select, update
from sqlalchemy.orm import declarative_base

from ...domain.enums import ResourceStatus
from ...domain.models import AuditEvent, ContentVersion, NormalizedDocument, Resource, ReviewAssignment
from ...ports.repositories import DocumentRepository, ResourceRepository, ReviewRepository, VersionRepository

Base = declarative_base()

class ResourceModel(Base):
    __tablename__ = "resources"
    resource_id = Column(String, primary_key=True)
    source_type = Column(String)
    source_url = Column(String)
    status = Column(String)
    content_hash = Column(String)
    submitted_at = Column(DateTime)
    updated_at = Column(DateTime)
    version = Column(Integer, default=1)
    __table_args__ = (UniqueConstraint("content_hash"), Index("ix_res_status", "status", "updated_at"))

class DocumentModel(Base):
    __tablename__ = "documents"
    resource_id = Column(String, ForeignKey("resources.resource_id"), primary_key=True)
    title = Column(String)
    blocks = Column(JSON)

class ContentVersionModel(Base):
    __tablename__ = "content_versions"
    version_id = Column(String, primary_key=True)
    resource_id = Column(String, ForeignKey("resources.resource_id"))
    version_number = Column(Integer)
    author_kind = Column(String)

class ReviewAssignmentModel(Base):
    __tablename__ = "review_assignments"
    assignment_id = Column(String, primary_key=True)
    resource_id = Column(String, ForeignKey("resources.resource_id"))
    reviewer_id = Column(String)
    priority = Column(Integer, default=0)
    completed_at = Column(DateTime)

class AuditEventModel(Base):
    __tablename__ = "audit_events"
    event_id = Column(String, primary_key=True)
    resource_id = Column(String, ForeignKey("resources.resource_id"))
    action = Column(String)
    at = Column(DateTime)


class SqlResourceRepository(ResourceRepository):
    def __init__(self, *, session_factory: object) -> None:
        self._session_factory = session_factory

    def add(self, resource: Resource) -> None:
        with self._session_factory() as s:
            s.add(ResourceModel(
                resource_id=resource.resource_id,
                source_type=resource.source_type,
                source_url=resource.source_url,
                status=str(resource.status),
                content_hash=resource.content_hash
            ))
            s.commit()

    def get(self, resource_id: str) -> Resource:
        with self._session_factory() as s:
            r = s.get(ResourceModel, resource_id)
            if not r:
                raise KeyError(f"{resource_id} not found")
            return Resource(r.resource_id, r.source_type, r.source_url, ResourceStatus(r.status), r.content_hash)

    def find_by_content_hash(self, content_hash: str) -> Resource | None:
        with self._session_factory() as s:
            r = s.execute(select(ResourceModel).where(ResourceModel.content_hash == content_hash)).scalar_one_or_none()
            return Resource(r.resource_id, r.source_type, r.source_url, ResourceStatus(r.status), r.content_hash) if r else None

    def save(self, resource: Resource) -> None:
        with self._session_factory() as s:
            ver = getattr(resource, 'version', 1)
            st = (update(ResourceModel)
                  .where(ResourceModel.resource_id == resource.resource_id, ResourceModel.version == ver)
                  .values(status=str(resource.status), version=ResourceModel.version + 1))
            if s.execute(st).rowcount == 0:
                raise ValueError("Concurrency conflict")
            s.commit()

    def list_by_status(self, status: ResourceStatus, *, limit: int = 100, offset: int = 0) -> list[Resource]:
        with self._session_factory() as s:
            rows = s.execute(select(ResourceModel).where(ResourceModel.status == str(status)).offset(offset).limit(limit)).scalars().all()
            return [Resource(r.resource_id, r.source_type, r.source_url, ResourceStatus(r.status), r.content_hash) for r in rows]


class SqlDocumentRepository(DocumentRepository):
    def save_document(self, document: NormalizedDocument) -> None:
        with self._session_factory() as s:
            doc = s.get(DocumentModel, document.resource_id) or DocumentModel(resource_id=document.resource_id)
            s.add(doc)
            s.commit()

    def get_document(self, resource_id: str) -> NormalizedDocument:
        with self._session_factory() as s:
            doc = s.get(DocumentModel, resource_id)
            if not doc:
                raise KeyError("Document not found")
            return NormalizedDocument(resource_id=doc.resource_id)


class SqlVersionRepository(VersionRepository):
    def save_version(self, version: ContentVersion) -> None:
        with self._session_factory() as s:
            v_num = (s.query(func.coalesce(func.max(ContentVersionModel.version_number), 0))
                     .filter_by(resource_id=version.resource_id).scalar()) + 1
            s.add(ContentVersionModel(
                version_id=f"{version.resource_id}_{v_num}",
                resource_id=version.resource_id,
                version_number=v_num
            ))
            s.commit()

    def get_latest(self, resource_id: str) -> ContentVersion | None:
        with self._session_factory() as s:
            v = s.execute(select(ContentVersionModel).where(ContentVersionModel.resource_id == resource_id).order_by(ContentVersionModel.version_number.desc())).scalar_one_or_none()
            return ContentVersion(resource_id=v.resource_id) if v else None

    def get_machine_version(self, resource_id: str) -> ContentVersion | None:
        with self._session_factory() as s:
            v = s.execute(select(ContentVersionModel).where(ContentVersionModel.resource_id == resource_id, ContentVersionModel.author_kind == "MACHINE")).scalar_one_or_none()
            return ContentVersion(resource_id=v.resource_id) if v else None

    def list_versions(self, resource_id: str) -> list[ContentVersion]:
        with self._session_factory() as s:
            rows = s.execute(select(ContentVersionModel).where(ContentVersionModel.resource_id == resource_id)).scalars().all()
            return [ContentVersion(r.resource_id) for r in rows]


class SqlReviewRepository(ReviewRepository):
    def create_assignment(self, assignment: ReviewAssignment) -> None:
        with self._session_factory() as s:
            s.add(ReviewAssignmentModel(assignment_id=assignment.assignment_id, resource_id=assignment.resource_id))
            s.commit()

    def get_assignment(self, assignment_id: str) -> ReviewAssignment:
        with self._session_factory() as s:
            a = s.get(ReviewAssignmentModel, assignment_id)
            if not a:
                raise KeyError("Not found")
            return ReviewAssignment(assignment_id=a.assignment_id, resource_id=a.resource_id)

    def claim_next(self, reviewer_id: str) -> ReviewAssignment | None:
        with self._session_factory() as s:
            st = (select(ReviewAssignmentModel)
                  .where(ReviewAssignmentModel.reviewer_id.is_(None), ReviewAssignmentModel.completed_at.is_(None))
                  .limit(1)
                  .with_for_update(skip_locked=True))
            row = s.execute(st).scalar_one_or_none()
            if not row:
                return None
            row.reviewer_id = reviewer_id
            s.commit()
            return ReviewAssignment(assignment_id=row.assignment_id, resource_id=row.resource_id)

    def save_assignment(self, assignment: ReviewAssignment) -> None:
        with self._session_factory() as s:
            a = s.get(ReviewAssignmentModel, assignment.assignment_id)
            if a:
                s.commit()

    def append_audit(self, event: AuditEvent) -> None:
        with self._session_factory() as s:
            s.add(AuditEventModel(event_id=event.event_id, resource_id=event.resource_id))
            s.commit()

    def list_audit(self, resource_id: str) -> list[AuditEvent]:
        with self._session_factory() as s:
            rows = s.execute(select(AuditEventModel).where(AuditEventModel.resource_id == resource_id)).scalars().all()
            return [AuditEvent(event_id=r.event_id, resource_id=r.resource_id) for r in rows]