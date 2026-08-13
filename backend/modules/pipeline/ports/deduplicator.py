"""
Port: Deduplicator — never process the same resource twice (PDF 3.1).

Dedup is not a nice-to-have. Every duplicate costs an ASR run, an MT call, and
— most expensively — a slot of human reviewer attention on content that was
already reviewed. It is the cheapest cost control in the pipeline.

TWO LEVELS, BOTH NEEDED
  1. URL-level, before fetching: cheapest possible check, saves the download.
  2. Content-level, after fetching: catches the same document served at two
     URLs, or a URL that redirects. Hash the NORMALIZED text, not the raw
     bytes — two HTML fetches of the same page differ by a timestamp or an ad
     slot and would hash differently while being the same content.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Deduplicator(ABC):
    """Computes and checks content identity."""

    @abstractmethod
    def compute_hash(self, *, source_url: str, content: bytes | str) -> str:
        """Return a stable content hash for dedup.

        TODO (junior dev):
          [ ] sha256 over normalized input: lowercase + strip the URL's tracking
              query params (utm_*, fbclid), collapse whitespace in text.
          [ ] Same input must ALWAYS give the same hash — no timestamps, no
              random salt, no dict iteration order in the digest.
          [ ] Document your normalization in this docstring when you write it.
              Changing it later invalidates every stored hash, so it is a
              migration, not a tweak.
        """
        raise NotImplementedError

    @abstractmethod
    def is_duplicate(self, content_hash: str) -> bool:
        """Return True if this hash has already entered the pipeline.

        NOTE: this is advisory, not a lock. The authoritative guard is the
        UNIQUE index on `resources.content_hash` — see `repositories.py`.
        Check here to fail fast and cheap; rely on the database to be correct.
        """
        raise NotImplementedError
