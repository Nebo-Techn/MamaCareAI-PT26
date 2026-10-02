"""Alembic environment script — migration context for the pipeline schema.

SETUP
1.  Set PIPELINE_DATABASE_URL (or pass ``-x dburl=...`` on the CLI).
2.  ``alembic upgrade head``  — create tables.
3.  ``alembic downgrade base`` — drop them.

The URL is read from ``PIPELINE_DATABASE_URL``, which defaults to the SQLite
path from `PipelineSettings.database_url`.  Production overrides it with a
PostgreSQL URL using the same env var — Alembic needs no code changes.

The migration script (`versions/0001_initial_schema.py`) calls
``Base.metadata.create_all`` so the schema is guaranteed to match the ORM
exactly.  No hand-written DDL = no drift between the migration and the code.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from modules.pipeline.adapters.storage.sql_repositories import Base

config = context.config
target_metadata = Base.metadata


def get_url() -> str:
    """Return the database URL, preferring an explicit -x argument."""
    x: dict[str, str] = context.get_x_argument(as_dictionary=True)
    if "dburl" in x:
        return x["dburl"]
    url = os.getenv("PIPELINE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if url:
        return url
    return "sqlite:///./data/pipeline.db"


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    raise NotImplementedError("offline mode is not supported for this project")
else:
    run_migrations_online()
