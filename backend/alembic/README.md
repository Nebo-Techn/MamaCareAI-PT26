# Alembic

Database migration scripts — only needed once structured relational data
(source register, evaluation logs, conversation history) moves from files or
SQLite into a real Postgres database. Don't set this up until
`backend/modules/storage` actually needs it; an empty migrations folder for a
database nobody has provisioned yet is exactly the kind of premature
scaffolding this rebuild was meant to remove.

**Owner track:** API/Bot track, if/when relational storage is needed.
**Sprint:** likely not before Sprint 3–4, if at all in the 8-week MVP.
