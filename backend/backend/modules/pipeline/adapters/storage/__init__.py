"""
Storage adapters (PDF 3.5) — object store, repositories, search index.

TWO STACKS BEHIND THE SAME PORTS:

    MVP (free, runs on a laptop)   Production (the PDF's stack)
    ---------------------------    ----------------------------
    filesystem_object_store        s3_object_store
    sql_repositories (SQLite)      sql_repositories (PostgreSQL)
    sqlite_search_index (FTS5)     opensearch_index

Note that the repository adapter is SHARED — SQLAlchemy speaks to both SQLite
and PostgreSQL, so the same file serves both. Only the connection URL changes.
That is the cheapest possible dev/prod parity, and it means a bug found on
SQLite is a real bug in the production code path, not a difference in a
throwaway dev implementation.
"""
