"""
SQLite FTS5 search index — the free MVP search backend.

PDF 3.5 specifies OpenSearch/Elasticsearch. Those need a running server and
real memory; docs/ARCHITECTURE.md says no budget is provisioned. SQLite's FTS5
gives genuine full-text search in a single file with no server at all, which is
the right call at MVP volume (hundreds to low thousands of documents).

WHEN TO SWITCH TO OPENSEARCH — decide on evidence, not vibes:
  - more than ~100k documents, or
  - search latency above ~500ms, or
  - you need faceting, aggregations, or real relevance tuning
Until one of those is true, OpenSearch is an ops burden bought with no benefit.
Record the switch in docs/DECISIONS.md when it happens.
"""

from __future__ import annotations

from ...ports.search_index import IndexedResource, SearchHit, SearchIndex


class SqliteSearchIndex(SearchIndex):
    """Full-text search over translated content using SQLite FTS5."""

    def __init__(self, *, database_path: str) -> None:
        # TODO: create the FTS5 virtual table if it does not exist:
        #
        #   CREATE VIRTUAL TABLE IF NOT EXISTS resource_fts USING fts5(
        #       resource_id UNINDEXED,
        #       title,
        #       translated_text,
        #       source_url UNINDEXED,
        #       status UNINDEXED,
        #       tokenize = 'unicode61 remove_diacritics 2'
        #   );
        #
        # UNINDEXED on the fields you filter/display but never search saves
        # index size and speeds up writes.
        #
        # `unicode61` handles Swahili's Latin script correctly. Do NOT use the
        # `porter` tokenizer — it is an ENGLISH stemmer, and stemming Swahili
        # with English rules mangles exactly the health vocabulary this project
        # depends on ("mimba", "uzazi"). This one config line is the difference
        # between search that works and search that quietly does not.
        self._database_path = database_path

    def index(self, resource: IndexedResource) -> None:
        """TODO:
        [ ] UPSERT by resource_id — DELETE then INSERT is the standard FTS5
            pattern, since FTS5 has no native upsert. Skipping the delete
            means every re-index adds a duplicate row and search returns the
            same document three times.
        [ ] Wrap in a transaction so a crash between delete and insert cannot
            lose the document from the index entirely.
        """
        raise NotImplementedError

    def search(
        self, query: str, *, limit: int = 20, offset: int = 0
    ) -> list[SearchHit]:
        """TODO:
        [ ] ESCAPE THE QUERY. FTS5 has its own syntax (AND, OR, NEAR, *, ")
            and unescaped user input either errors or does something
            surprising. Quote the terms.
        [ ] SELECT ... WHERE resource_fts MATCH ? ORDER BY rank
        [ ] Use snippet() for the highlighted excerpt and bm25() for the
            score, so the review UI can show context around the match.
        [ ] Return [] for an empty query rather than raising — an empty
            search box is a normal state.
        """
        raise NotImplementedError

    def remove(self, resource_id: str) -> None:
        """TODO: DELETE by resource_id. Must not error when already absent."""
        raise NotImplementedError
