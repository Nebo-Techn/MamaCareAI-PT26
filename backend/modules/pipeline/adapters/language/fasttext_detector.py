"""FastText language detector adapter implementation."""

from modules.pipeline.domain.models import DetectionResult


class FastTextDetector:
    """Adapter for detecting language using fastText."""

    def __init__(self, model_path: str, top_k: int = 3) -> None:
        self._model_path = model_path
        self._top_k = top_k

    def detect(self, text: str) -> DetectionResult:
        """Detect language using fastText.

        Strips '__label__' prefix and returns DetectionResult.
        """
        raise NotImplementedError