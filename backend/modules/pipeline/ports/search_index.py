"""
Port: SearchIndex — full-text search over translated Swahili content (PDF 3.5, 3.7).

Two consumers:
  1. The review team, finding and filtering work.
  2. Downstream systems — for MamaCare AI specifically, this is the handoff
     point where published Swahili resources feed `modules/knowledge` for
     chunking and embedding.

MVP binds this to SQLite FTS5 (free, no server). Production binds it to
OpenSearch. Keep the interface narrow enough that both are honest
implementations — do not let OpenSearch-specific query DSL leak into it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IndexedResource:
    """The searchable projection of a resource. A read model, not the source of truth.

    Losing the index must never mean losing data — it is rebuildable from
    Postgres + object storage. Write a `reindex` management command early and
    prove that claim before you need it.
    """

    resource_id: str
    title: str | None
    translated_text: str
    source_url: str
    status: str
    version_number: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchHit:
    resource_id: str
    title: str | None
    snippet: str          # highlighted excerpt around the match
    score: float


class SearchIndex(ABC):
    """Full-text index over translated content."""

    @abstractmethod
    def index(self, resource: IndexedResource) -> None:
        """Add or replace a resource in the index.

        Upsert by resource_id, so re-indexing after a human edit replaces the
        old text instead of creating a duplicate hit.
        """
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, *, limit: int = 20, offset: int = 0) -> list[SearchHit]:
        """Full-text search over indexed Swahili text.

        TODO (junior dev): configure a Swahili-appropriate analyzer. The default
        English analyzer stems Swahili badly, and Swahili's agglutinative
        morphology means naive stemming hurts recall on exactly the health
        vocabulary this project cares about. Verify with real queries from
        `eval/test_questions/`, not with English test strings.
        """
        raise NotImplementedError

    @abstractmethod
    def remove(self, resource_id: str) -> None:
        """Delete a resource from the index.

        Needed when content is unpublished or the compliance gate retroactively
        blocks it. Must not error when the document is already absent.
        """
        raise NotImplementedError
