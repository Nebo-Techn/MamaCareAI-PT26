"""
Port: ObjectStore — where raw files live (PDF 3.5).

Original PDFs, HTML snapshots, audio. Big, immutable blobs that must never go
into a database column.

MVP binds this to the local filesystem (free, zero setup). Production binds it
to S3. The stages cannot tell the difference, which is the entire point.

KEY DISCIPLINE: the pipeline passes around KEYS (short strings), never bytes.
A Job message carries "raw/2026/08/<resource_id>.pdf", not 40MB of PDF.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ObjectStore(ABC):
    """Content-addressed blob storage for raw pipeline artifacts."""

    @abstractmethod
    def put(self, key: str, content: bytes, *, content_type: str) -> str:
        """Store `content` at `key` and return the key.

        Contract:
          - Idempotent: writing the same key twice with the same bytes is fine
            and is NOT an error. Retries depend on this.
          - Treat stored objects as immutable. To change content, write a new
            key — never mutate an existing one, because versions reference keys.

        TODO: use the key convention in `adapters/storage/keys.py` so objects
        stay browsable by date and resource, e.g.
        "raw/{yyyy}/{mm}/{resource_id}/original.pdf".
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve the bytes stored at `key`.

        Raise a PermanentError if the key does not exist — a missing object is
        a data-integrity problem, not something to retry into oblivion.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if `key` is present. Used to skip redundant re-fetching."""
        raise NotImplementedError
