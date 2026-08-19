"""
Self-hosted NLLB-200 translator (PDF 3.4).

"a self-hosted NLLB-200 model for cost control, data privacy, or offline
operation; NLLB has solid Swahili support".

WHY THIS IS THE DEFAULT FOR MAMACARE AI
docs/ARCHITECTURE.md commits to free-tier and open-source only — no budget is
provisioned. NLLB-200 runs locally with no per-call cost, which makes it the
only option that scales with corpus size instead of with budget. Cloud MT stays
available behind the same port if that changes.

MODEL SIZES:
  nllb-200-distilled-600M  ~2.4GB  runs on CPU, the practical starting point
  nllb-200-1.3B            ~5.5GB  better quality, wants a GPU
  nllb-200-3.3B           ~17.5GB  GPU only

Start with 600M. Measure quality against real reviewer edits (see
`services/feedback_export.py`) before spending on anything bigger — the
% approved-without-edit metric will tell you whether a larger model is worth
it far more reliably than any benchmark.

NLLB USES ITS OWN LANGUAGE CODES: Swahili is "swh_Latn", not "sw"; English is
"eng_Latn". Map them inside this adapter. Nothing outside this file should ever
see an NLLB-specific code — that is what keeps the port swappable.
"""

from typing import ClassVar

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from ...ports.translator import (
    TransientError,
    TranslatedChunk,
    TranslationError,
    Translator,
)


class NllbTranslator(Translator):
    """Local NLLB-200 translation via transformers."""

    # TODO: fill in the ISO -> NLLB (FLORES-200) code map for every source
    # language we actually ingest. Keep it here and nowhere else.
    LANGUAGE_CODES: ClassVar[dict[str, str]] = {
        "sw": "swh_Latn",
        "en": "eng_Latn",
        "fr": "fra_Latn",
        # TODO: add the rest as sources are added to the register.
    }

    def __init__(
        self,
        *,
        model_name: str = "facebook/nllb-200-distilled-600M",
        device: str = "cpu",
        batch_size: int = 16,
        max_length: int = 512,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._max_length = max_length
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")
        if max_length < 1:
            raise ValueError("max_length must be greater than zero")

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self._model.to(device)
            self._model.eval()
        except Exception as exc:
            raise TranslationError(
                f"Unable to load translation model {model_name!r}: {exc}"
            ) from exc

    @property
    def engine_name(self) -> str:
        return f"nllb:{self._model_name}"

    def supports(self, source_language: str, target_language: str) -> bool:
        return (
            source_language in self.LANGUAGE_CODES
            and target_language in self.LANGUAGE_CODES
        )

    def translate_batch(
        self, texts: list[str], *, source_language: str, target_language: str = "sw"
    ) -> list[TranslatedChunk]:
        """Translate a batch locally.

        TODO (junior dev):
          [ ] Map ISO codes to NLLB codes; raise TranslationError on unknown.
          [ ] Set the tokenizer's src_lang, and force the target via
              `forced_bos_token_id` for the target language. Getting this wrong
              produces confident output in the WRONG LANGUAGE — the model does
              not error, it just translates into something else. Assert on it
              in a test with a known input.
          [ ] Process in sub-batches of self._batch_size. One giant batch will
              OOM on CPU.
          [ ] SORT BY LENGTH within a batch before padding. Mixing a 10-token
              and a 500-token input pads everything to 500 and wastes most of
              the compute. This one change is often a 2-3x speedup.
          [ ] Return EXACTLY len(texts) results IN THE SAME ORDER. If you
              sorted for batching, restore the original order before returning.
              This is the single easiest way to silently corrupt a document,
              and it will look like a translation-quality problem rather than
              an ordering bug. Write a test with distinctly-lengthed inputs.
          [ ] confidence=None — NLLB gives no calibrated confidence. Do NOT
              fabricate one; the review queue prioritizes on it, and a made-up
              number is worse than no number.
          [ ] Wrap OOM/CUDA errors as TransientError (a retry on a less loaded
              worker may genuinely succeed).

        THREAD SAFETY: a transformers model is NOT safe to call concurrently
        from multiple threads. One model instance per worker PROCESS. If you
        need more throughput, run more worker processes, not more threads.
        """
        if not self.supports(source_language, target_language):
            raise TranslationError(
                f"Unsupported language pair: {source_language}->{target_language}"
            )
        if not texts:
            return []

        source_code = self.LANGUAGE_CODES[source_language]
        target_code = self.LANGUAGE_CODES[target_language]
        try:
            self._tokenizer.src_lang = source_code
            # NLLB's tokenizer exposes the target language token id through
            # convert_tokens_to_ids; using it avoids relying on tokenizer
            # implementation-specific attributes.
            forced_bos_token_id = self._tokenizer.convert_tokens_to_ids(target_code)
            if forced_bos_token_id is None:
                raise TranslationError(f"Unknown NLLB target code: {target_code}")

            results: list[str] = [""] * len(texts)
            for start in range(0, len(texts), self._batch_size):
                indexes = list(range(start, min(start + self._batch_size, len(texts))))
                indexes.sort(key=lambda i: len(texts[i]), reverse=True)
                batch = [texts[i] for i in indexes]
                encoded = self._tokenizer(
                    batch,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=self._max_length,
                )
                encoded = {key: value.to(self._device) for key, value in encoded.items()}
                with torch.inference_mode():
                    generated = self._model.generate(
                        **encoded,
                        forced_bos_token_id=forced_bos_token_id,
                        max_length=self._max_length,
                    )
                decoded = self._tokenizer.batch_decode(
                    generated, skip_special_tokens=True
                )
                for index, translation in zip(indexes, decoded):
                    results[index] = translation
            return [TranslatedChunk(text=text, translated_text=translation, confidence=None)
                    for text, translation in zip(texts, results)]
        except TranslationError:
            raise
        except (RuntimeError, torch.cuda.OutOfMemoryError) as exc:
            if "out of memory" in str(exc).lower() or isinstance(exc, torch.cuda.OutOfMemoryError):
                raise TransientError(f"NLLB translation ran out of memory: {exc}") from exc
            raise TranslationError(f"NLLB translation failed: {exc}") from exc
        except Exception as exc:
            raise TranslationError(f"NLLB translation failed: {exc}") from exc
