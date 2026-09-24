"""FastText language detector adapter implementation."""

import re
import sys

from ...ports.language_detector import DetectionResult


class FastTextDetector:
    """Adapter for detecting language using fastText.

    NOTE: This implementation requires the fasttext library and the language
    identification model file (lid.176.bin). If fasttext is not available,
    this falls back to langdetect library for language detection.

    Requirements:
    - Primary: pip install fasttext (requires Microsoft Visual C++ 14.0 or greater)
    - Fallback: pip install langdetect (pure Python, no compilation needed)
    - Download model: https://dl.fbafiles.com/facebook/fasttext/supervised/models/lid.176.bin
    - Save to: backend/models/lid.176.bin
    """

    def __init__(self, model_path: str, top_k: int = 3) -> None:
        self._model_path = model_path
        self._top_k = top_k
        self._model = None
        self._use_langdetect = False
        self._use_heuristic = False
        self._load_model()

    def _load_model(self) -> None:
        """Load fastText model or fallback to langdetect/heuristic detection."""
        try:
            import fasttext
            self._model = fasttext.load_model(self._model_path)
        except (ImportError, OSError, RuntimeError, ValueError) as e:
            # Try langdetect as first fallback
            try:
                import importlib.util
                if importlib.util.find_spec("langdetect") is not None:
                    self._use_langdetect = True
                    print(f"Warning: Could not load fastText model from {self._model_path}: {e}", file=sys.stderr)
                    print("Falling back to langdetect library for language detection.", file=sys.stderr)
                else:
                    raise ImportError("langdetect not available")
            except ImportError:
                # Use heuristic as last fallback
                self._use_heuristic = True
                print(f"Warning: Could not load fastText model from {self._model_path}: {e}", file=sys.stderr)
                print("langdetect not available. Falling back to heuristic-based language detection for testing.", file=sys.stderr)

    def detect(self, text: str) -> DetectionResult:
        """Detect language using fastText, langdetect, or heuristic fallback.

        Strips '__label__' prefix and returns DetectionResult.
        """
        if not text or not text.strip():
            return DetectionResult(language="unknown", confidence=0.0, alternatives=())

        if self._use_langdetect:
            return self._langdetect_detect(text)

        if self._use_heuristic:
            return self._heuristic_detect(text)

        try:
            # fastText predict returns (labels, probabilities)
            labels, probabilities = self._model.predict(text, k=self._top_k)

            # Get top result
            top_label = labels[0]
            top_prob = probabilities[0]

            # Strip '__label__' prefix
            language = top_label.replace("__label__", "")

            return DetectionResult(language=language, confidence=float(top_prob), alternatives=())
        except (ValueError, AttributeError, IndexError) as e:
            raise RuntimeError(f"Language detection failed: {e}") from e

    def _langdetect_detect(self, text: str) -> DetectionResult:
        """Language detection using langdetect library.

        langdetect is a pure Python library that doesn't require compilation.
        It provides basic language detection for 55 languages.
        """
        try:
            from langdetect import detect, detect_langs

            # Get the most likely language
            language = detect(text)

            # Get confidence scores from all detected languages
            langs = detect_langs(text)
            if langs:
                confidence = langs[0].prob
                # Create alternatives from other detected languages
                alternatives = tuple((lang.lang, lang.prob) for lang in langs[1:self._top_k])
            else:
                confidence = 0.5
                alternatives = ()

            # Convert langdetect codes to ISO 639-1 if needed
            # langdetect uses standard codes like 'en', 'sw', etc.
            return DetectionResult(language=language, confidence=confidence, alternatives=alternatives)

        except Exception as e:  # noqa: BLE001
            # If langdetect fails, fall back to heuristic
            # We catch Exception here because langdetect can raise various exceptions
            # including LangDetectException, AttributeError, etc. that we don't
            # want to explicitly import or handle separately.
            print(f"Warning: langdetect failed: {e}. Falling back to heuristic detection.", file=sys.stderr)
            return self._heuristic_detect(text)

    def _heuristic_detect(self, text: str) -> DetectionResult:
        """Fallback heuristic-based language detection for testing.

        This is a simple implementation that can be used when neither fastText
        nor langdetect are available. It uses basic character patterns to detect
        common languages.
        """
        # Count whole words. The previous substring check treated English words
        # such as "normal" as Swahili because they contain "na".
        words = re.findall(r"[a-zA-Z]+", text.casefold())
        english_words = {
            "about", "and", "are", "can", "during", "for", "from", "in",
            "is", "of", "on", "that", "the", "this", "to", "was", "were",
            "will", "with", "you", "your",
        }
        swahili_words = {
            "afya", "asante", "habari", "hii", "kama", "katika", "kila",
            "kwa", "lakini", "mama", "mimba", "mtoto", "mwaka", "na",
            "ni", "siku", "wa", "ya", "yako", "za",
        }
        english_score = sum(word in english_words for word in words)
        swahili_score = sum(word in swahili_words for word in words)

        english_signal = english_score >= 2 or "the" in words
        swahili_signal = swahili_score >= 2 or bool(
            {"asante", "habari", "kwa"}.intersection(words)
        )

        if english_signal and english_score > swahili_score * 1.5:
            confidence = min(0.99, 0.75 + (english_score - swahili_score) / 20)
            return DetectionResult(
                language="en",
                confidence=confidence,
                alternatives=(("sw", 1.0 - confidence),),
            )

        if swahili_signal and swahili_score > english_score * 1.5:
            confidence = min(0.99, 0.75 + (swahili_score - english_score) / 20)
            return DetectionResult(
                language="sw",
                confidence=confidence,
                alternatives=(("en", 1.0 - confidence),),
            )

        # Default to unknown with low confidence
        return DetectionResult(language="unknown", confidence=0.3, alternatives=())
