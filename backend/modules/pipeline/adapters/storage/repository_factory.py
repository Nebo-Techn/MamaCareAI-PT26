"""
Repository factory — one place to build the four SQL repositories.

Only imported by `container.build_container()` and Alembic's `env.py`, so that
the session-factory construction, the engine lifecycle, and the metadata
binding live here rather than being re-implemented per consumer.

WHY A FACTORY AND NOT A DEFAULT ENGINE
`container.build_container()` is called once per process at startup. A module
-level singleton engine would work, but it makes it impossible to create a
second engine in the same process (e.g. Alembic migrations while the container
is already running, or test fixtures creating a temporary engine alongside the
live one). The factory takes the URL each time, so callers can own the
lifecycle independently.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .sql_repositories import (
    SqlDocumentRepository,
    SqlResourceRepository,
    SqlReviewRepository,
    SqlVersionRepository,
)


def build_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for the given URL.

    The URL is taken from `PipelineSettings.database_url`, which defaults to
    `sqlite:///./data/pipeline.db` and must be flipped to
    `postgresql+psycopg://…` in production.  This function never reads the
    settings itself so it stays testable without patching config.
    """
    return create_engine(database_url, echo=False)


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Return a session factory bound to an engine for *database_url*.

    The returned factory is an instance of `sessionmaker`, so callers create
    sessions with ``factory()``.  A new engine is created per call — callers
    that need a shared engine should call `build_engine` once and pass it to
    `sessionmaker(bind=engine)` directly.
    """
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, expire_on_commit=False)


def build_repositories(
    database_url: str,
) -> dict[str, Any]:
    """Build the four SQL repositories backed by a single engine.

    Returns a dict so `container.build_container()` can splat it into
    ``Container(resources=..., documents=..., ...)`` without a positional-args
    signature that would change every time a repository is added.

    The engine created here is kept alive for the lifetime of the session
    factory that references it; the caller is responsible for calling
    ``engine.dispose()`` on shutdown.
    """
    engine = build_engine(database_url)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    return {
        "resources": SqlResourceRepository(session_factory=factory),
        "documents": SqlDocumentRepository(session_factory=factory),
        "versions": SqlVersionRepository(session_factory=factory),
        "reviews": SqlReviewRepository(session_factory=factory),
    }
