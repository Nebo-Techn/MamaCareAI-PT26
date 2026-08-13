"""
Content deduplicator (PDF 3.1) — the cheapest cost control in the pipeline.

Every duplicate that gets through costs an ASR run, an MT call, and a slot of
human reviewer attention on content that was already reviewed. The last of
those is the expensive one.

NORMALIZE BEFORE HASHING — THIS IS THE WHOLE FILE.
Hashing raw bytes catches almost nothing. Two fetches of the same web page
differ by a timestamp, a session id, or an ad slot, so their bytes differ while
the content is identical. Normalize aggressively first, then hash.

WARNING: the normalization rules below ARE the hash. Changing them invalidates
every stored hash in the database, so a change is a migration, not a tweak.
Document any change in docs/DECISIONS.md.
"""

from __future__ import annotations

from ...ports.deduplicator import Deduplicator
from ...ports.repositories import ResourceRepository


class ContentDeduplicator(Deduplicator):
    """Hash-based deduplication against the resource repository."""

    # Tracking parameters that change per visit but never change the content.
    STRIP_QUERY_PARAMS: frozenset[str] = frozenset(
        {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
         "fbclid", "gclid", "ref", "session", "sessionid"}
    )

    def __init__(self, *, resources: ResourceRepository) -> None:
        self._resources = resources

    def compute_hash(self, *, source_url: str, content: bytes | str) -> str:
        """Return a stable sha256 over normalized URL + content.

        TODO (junior dev) — normalization steps, in order:

          URL:
            [ ] lowercase scheme and host (paths stay case-sensitive)
            [ ] drop the fragment (#section) — same document
            [ ] remove STRIP_QUERY_PARAMS, then sort the remaining params so
                ?a=1&b=2 and ?b=2&a=1 hash identically
            [ ] strip a trailing slash
            [ ] drop "www."

          CONTENT (when non-empty — an empty content means URL-only hashing):
            [ ] decode as UTF-8 with errors="ignore" if bytes
            [ ] NFC normalize
            [ ] lowercase
            [ ] collapse all whitespace runs to a single space, strip ends

          THEN: sha256(normalized_url + "\\x00" + normalized_content).hexdigest()
          The null separator prevents a boundary collision between the two parts.

        MUST BE DETERMINISTIC. No timestamps, no randomness, no dict iteration
        order in the digest. Test it: the same input must produce the same hash
        across processes and across restarts.

        FUTURE (do not build yet): near-duplicate detection via SimHash or
        MinHash, for pages that differ only by a "last updated" date. Only worth
        it if exact-hash dedup proves insufficient in practice — measure first.
        """
        raise NotImplementedError

    def is_duplicate(self, content_hash: str) -> bool:
        """TODO: `self._resources.find_by_content_hash(content_hash) is not None`.

        Remember this is only a fast pre-check. The authoritative guarantee is
        the UNIQUE index on resources.content_hash — under concurrency, two
        workers can both see False here, and the database is what stops them.
        """
        raise NotImplementedError
