"""
OpenSearch index — the production search backend (PDF 3.5).

Swap in with PIPELINE_SEARCH_BACKEND=opensearch. No stage changes.

THE ANALYZER IS THE ENTIRE GAME HERE.
An index with the default English analyzer will return plausible-looking but
subtly wrong results for Swahili, and nobody will notice for weeks because the
search box does return *something*. Configure the analyzer deliberately, then
verify against real queries from `eval/test_questions/` — not English test
strings, which will pass regardless.

Swahili is agglutinative: prefixes and infixes carry grammatical meaning
("mtoto"/"watoto", "kuzaa"/"anazaa"). English stemming rules do real damage to
that. Start with a Unicode/ICU analyzer plus lowercase folding, and add a
Swahili stopword list. Do not enable an English stemmer.
"""

from __future__ import annotations

from ...ports.search_index import IndexedResource, SearchHit, SearchIndex


class OpenSearchIndex(SearchIndex):
    """Full-text search backed by OpenSearch/Elasticsearch."""

    def __init__(
        self,
        *,
        hosts: list[str],
        index_name: str = "mamacare-resources",
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        # TODO: build the client once. Do NOT create the index implicitly on
        # first write — an auto-created index gets a guessed mapping with the
        # wrong analyzer, and fixing it later means a full reindex.
        self._index_name = index_name

    def ensure_index(self) -> None:
        """Create the index with an explicit mapping. Call at startup.

        TODO (junior dev):
          [ ] Define the mapping explicitly:
                - translated_text: text, with the Swahili analyzer
                - title:           text, same analyzer
                - resource_id/status/source_url: keyword (exact match, filters)
                - version_number:  integer
          [ ] Define the custom analyzer: icu_tokenizer + lowercase +
              Swahili stopwords. NO English stemmer.
          [ ] Make this idempotent — safe to call on every startup.
          [ ] Mappings CANNOT be changed in place. Getting this right before
              the first document is indexed saves a migration later; plan for
              an alias + reindex flow if it has to change anyway.
        """
        raise NotImplementedError

    def index(self, resource: IndexedResource) -> None:
        """TODO: index with id=resource_id (upsert semantics for free).

        For bulk operations use the `bulk` helper — indexing documents one at a
        time is an HTTP round trip each and will be the bottleneck during a
        reindex of the whole corpus.
        """
        raise NotImplementedError

    def search(
        self, query: str, *, limit: int = 20, offset: int = 0
    ) -> list[SearchHit]:
        """TODO:
        [ ] multi_match across title^2 and translated_text (title boosted —
            a match in the title is a stronger signal).
        [ ] Enable highlighting to populate `snippet`.
        [ ] Use from/size for paging, and be aware of the 10k deep-paging
            limit; use search_after if a caller ever needs to go past it.
        [ ] Map connection errors to TransientError. Search being briefly
            down must not fail the pipeline — it is a derived read model.
        """
        raise NotImplementedError

    def remove(self, resource_id: str) -> None:
        """TODO: delete by id; treat 404 as success (idempotent removal)."""
        raise NotImplementedError
