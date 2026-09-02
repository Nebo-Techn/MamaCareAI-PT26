"""Self-hosted NLLB-200 translation adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from ...domain.errors import TransientError, TranslationError
from ...ports.translator import TranslatedChunk, Translator


class NllbTranslator(Translator):
    """Translate locally with an NLLB-200 Transformers model.

    The default is a project-local model directory. Pass a Hugging Face model
    identifier instead when an online download is intentional.
    """

    LANGUAGE_CODES: ClassVar[dict[str, str]] = {
        "sw": "swh_Latn",
        "en": "eng_Latn",
        "fr": "fra_Latn",
    }

    def __init__(
        self,
        *,
        model_name: str = "./models/nllb-200",
        device: str = "cpu",
        batch_size: int = 16,
        max_length: int = 512,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if max_length < 1:
            raise ValueError("max_length must be at least 1")
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "NLLB translation requires torch, transformers, and sentencepiece. "
                "Install the project dependencies with `uv sync` or `uv add ...`."
            ) from exc

        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._max_length = max_length
        self._torch: Any = torch

        model_path = Path(model_name)
        is_local_model = model_path.is_absolute() or model_name.startswith((".", "\\", "./", ".\\"))
        if is_local_model and not model_path.is_dir():
            raise FileNotFoundError(
                f"NLLB model directory does not exist: {model_path.resolve()}. "
                "Download nllb-200-distilled-600M there or pass a model ID."
            )
        try:
            self._tokenizer: Any = AutoTokenizer.from_pretrained(model_name)
            self._model: Any = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self._model.to(self._device)
            self._model.eval()
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Could not load NLLB model {model_name!r}: {exc}") from exc

    @property
    def engine_name(self) -> str:
        return f"nllb:{self._model_name}"

    def supports(self, source_language: str, target_language: str) -> bool:
        return (
            source_language.lower() in self.LANGUAGE_CODES
            and target_language.lower() in self.LANGUAGE_CODES
        )

    def translate_batch(
        self, texts: list[str], *, source_language: str, target_language: str = "sw"
    ) -> list[TranslatedChunk]:
        """Translate locally, reducing padding without changing input order.

        A model instance must be used by one worker process at a time; do not
        call this method concurrently from several threads.
        """
        source = source_language.lower()
        target = target_language.lower()
        if not self.supports(source, target):
            raise TranslationError(
                f"NLLB does not support translation from {source_language!r} to {target_language!r}"
            )
        if not all(isinstance(text, str) for text in texts):
            raise TranslationError("NLLB translation inputs must all be strings")
        if not texts:
            return []

        source_code = self.LANGUAGE_CODES[source]
        target_code = self.LANGUAGE_CODES[target]
        try:
            target_token_id = self._tokenizer.convert_tokens_to_ids(target_code)
            if target_token_id is None or target_token_id == self._tokenizer.unk_token_id:
                raise TranslationError(f"NLLB tokenizer has no token for target language {target!r}")

            results: list[TranslatedChunk | None] = [None] * len(texts)
            indexed = sorted(enumerate(texts), key=lambda item: len(item[1]))
            self._tokenizer.src_lang = source_code
            for start in range(0, len(indexed), self._batch_size):
                batch = indexed[start : start + self._batch_size]
                encoded = self._tokenizer(
                    [text for _, text in batch],
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=self._max_length,
                )
                encoded = {name: value.to(self._device) for name, value in encoded.items()}
                with self._torch.no_grad():
                    generated = self._model.generate(
                        **encoded,
                        forced_bos_token_id=target_token_id,
                        max_length=self._max_length,
                    )
                translations = self._tokenizer.batch_decode(generated, skip_special_tokens=True)
                if len(translations) != len(batch):
                    raise TransientError("NLLB returned an unexpected number of translations")
                for (index, _), translation in zip(batch, translations):
                    results[index] = TranslatedChunk(text=translation, confidence=None)

            if any(result is None for result in results):
                raise TransientError("NLLB did not produce every translation")
            return [result for result in results if result is not None]
        except TranslationError:
            raise
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() or "cuda" in str(exc).lower():
                raise TransientError(f"NLLB inference failed transiently: {exc}") from exc
            raise
