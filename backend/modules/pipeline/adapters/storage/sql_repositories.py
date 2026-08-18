from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
    update,
)
from sqlalchemy.orm import declarative_base

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


class SqlResourceRepository(ResourceRepository):
    def __init__(self, session):
        self.session = session

    def add(self, resource: Resource) -> None:
        model = ResourceModel(
            resource_id=resource.resource_id,
            source_type=resource.source_type,
            source_url=resource.source_url,
            status=resource.status.value,
            content_hash=resource.content_hash,
            submitted_at=resource.submitted_at,
            updated_at=resource.updated_at,
        )
        self.session.add(model)

    def get_by_id(self, resource_id: str) -> Resource | None:
        model = self.session.query(ResourceModel).get(resource_id)
        if not model:
            return None
        return Resource(
            resource_id=model.resource_id,
            source_type=model.source_type,
            source_url=model.source_url,
            status=ResourceStatus(model.status),
            content_hash=model.content_hash,
            submitted_at=model.submitted_at,
            updated_at=model.updated_at,
        )


class SqlDocumentRepository(DocumentRepository):
    def __init__(self, session):
        self.session = session

    def add(self, document: NormalizedDocument) -> None:
        pass

    def get_by_id(self, document_id: str) -> NormalizedDocument | None:
        return None


class SqlVersionRepository(VersionRepository):
    def __init__(self, session):
        self.session = session

    def add(self, version: ContentVersion) -> None:
        pass

    def get_by_id(self, version_id: str) -> ContentVersion | None:
        return None


class SqlReviewRepository(ReviewRepository):
    def __init__(self, session):
        self.session = session

    def add_assignment(self, assignment: ReviewAssignment) -> None:
        pass

    def get_assignment_by_id(self, assignment_id: str) -> ReviewAssignment | None:
        return None

    def add_event(self, event: AuditEvent) -> None:
        pass