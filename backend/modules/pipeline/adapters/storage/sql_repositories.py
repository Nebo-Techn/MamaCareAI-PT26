"""SQLAlchemy repositories implementation for pipeline storage."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base model for pipeline storage."""



class ResourceModel(Base):
    """SQL model for PipelineResource."""

    __tablename__ = "pipeline_resources"

    resource_id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class JobModel(Base):
    """SQL model for PipelineJob."""

    __tablename__ = "pipeline_jobs"

    job_id = Column(String, primary_key=True)
    stage = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)