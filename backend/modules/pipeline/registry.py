from __future__ import annotations

import logging

from .domain.enums import SourceType
from .domain.errors import ExtractionError, UnsupportedSourceType
from .ports.extractor import ContentExtractor
from .ports.fetcher import SourceFetcher

logger = logging.getLogger(__name__)


class FetcherRegistry:
    def __init__(self) -> None:
        self._fetchers: dict[SourceType, SourceFetcher] = {}

    def register(self, fetcher: SourceFetcher) -> None:
        source_type = fetcher.source_type
        if source_type in self._fetchers:
            raise ValueError(
                f"Fetcher already registered for source type: {source_type.value}"
            )

        self._fetchers[source_type] = fetcher

    def get(self, source_type: SourceType) -> SourceFetcher:
        try:
            return self._fetchers[source_type]
        except KeyError as exc:
            raise UnsupportedSourceType(
                f"No fetcher registered for source type: {source_type.value}"
            ) from exc


class ExtractorRegistry:
    def __init__(self) -> None:
        self._extractors: list[tuple[int, ContentExtractor]] = []

    def register(self, extractor: ContentExtractor, *, priority: int = 50) -> None:
        self._extractors.append((priority, extractor))
        self._extractors.sort(key=lambda item: item[0], reverse=True)

    def select(self, content_type: str, content: bytes) -> ContentExtractor:
        for _priority, extractor in self._extractors:
            if extractor.can_handle(content_type, content):
                logger.debug(
                    "Selected extractor %s for content type %s",
                    type(extractor).__name__,
                    content_type,
                )
                return extractor

        raise ExtractionError(f"No extractor can handle content type: {content_type}")
