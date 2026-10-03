"""Initial pipeline schema.

Revision ID: 0001
Revises:
Create Date: 2026-10-02

Uses the ORM's own Base.metadata to create all tables.  This means:

* **One source of truth**: the schema is defined once in
  `sql_repositories.py`'s `Base`, not hand-typed twice in a migration.
* **No drift**: changing a column in the ORM is automatically reflected
  in the migration — and vice versa (any mismatch breaks `test_migrations.py`).
* **Dialect-aware types**: `TIMESTAMP(timezone=True)` and JSON/JSONB are
  already on the ORM columns, so `TIMESTAMPTZ` lands on PostgreSQL without
  any extra DDL.
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from modules.pipeline.adapters.storage.sql_repositories import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from modules.pipeline.adapters.storage.sql_repositories import Base

    Base.metadata.drop_all(bind=op.get_bind())
