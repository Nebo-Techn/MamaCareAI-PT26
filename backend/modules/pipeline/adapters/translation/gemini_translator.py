"""Gemini-backed translation adapter."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ...domain.errors import (
    PermanentError,
    ProviderRateLimited,
    TransientError,
    TranslationError,
)
from ...ports.translator import TranslatedChunk, Translator


class GeminiTranslator(Translator):
    """Translate batches with the Gemini ``generateContent`` REST API."""

    _SUPPORTED_LANGUAGES = frozenset({"en", "sw"})

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash",
        batch_size: int = 16,
        timeout_seconds: float = 60.0,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Gemini translation requires a non-empty API key")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self._model = model
        self._batch_size = batch_size
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            transport=transport,
        )

    @property
    def engine_name(self) -> str:
        return f"gemini:{self._model}"

    def supports(self, source_language: str, target_language: str) -> bool:
        return (
            source_language.casefold() in self._SUPPORTED_LANGUAGES
            and target_language.casefold() in self._SUPPORTED_LANGUAGES
            and source_language.casefold() != target_language.casefold()
        )

    def translate_batch(
        self,
        texts: list[str],
        *,
        source_language: str,
        target_language: str = "sw",
    ) -> list[TranslatedChunk]:
        if not self.supports(source_language, target_language):
            raise TranslationError(
                f"Gemini translation does not support {source_language!r} "
                f"to {target_language!r}"
            )
        if not all(isinstance(text, str) for text in texts):
            raise TranslationError("Gemini translation inputs must all be strings")
        if not texts:
            return []

        results: list[TranslatedChunk] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            translations = self._translate_request(
                batch,
                source_language=source_language,
                target_language=target_language,
            )
            results.extend(TranslatedChunk(text=text) for text in translations)
        return results

    def _translate_request(
        self,
        texts: list[str],
        *,
        source_language: str,
        target_language: str,
    ) -> list[str]:
        prompt = (
            "Translate every item in the JSON array from "
            f"{source_language} to {target_language}. Preserve meaning, medical "
            "terminology, headings, lists, numbers, and paragraph breaks. Do not "
            "summarize, omit, explain, or add information. Return only a JSON array "
            "of translated strings in exactly the same order and with exactly the "
            f"same number of items. Input:\n{json.dumps(texts, ensure_ascii=False)}"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
            },
        }
        try:
            response = self._client.post(
                f"/models/{self._model}:generateContent", json=payload
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise TransientError(f"Gemini request failed: {exc}") from exc

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            try:
                retry_seconds = float(retry_after) if retry_after else None
            except ValueError:
                retry_seconds = None
            raise ProviderRateLimited(
                "Gemini quota or rate limit exceeded",
                retry_after_seconds=retry_seconds,
            )
        if response.status_code in {401, 403}:
            raise PermanentError(
                f"Gemini authentication failed (HTTP {response.status_code}): "
                f"{self._error_message(response)}. Check or rotate GEMINI_API_KEY "
                "and ensure the Gemini API is enabled for its Google project"
            )
        if response.status_code >= 500:
            raise TransientError(
                f"Gemini service returned HTTP {response.status_code}"
            )
        if response.status_code >= 400:
            raise TranslationError(
                f"Gemini request returned HTTP {response.status_code}: "
                f"{self._error_message(response)}"
            )

        try:
            body: dict[str, Any] = response.json()
            parts = body["candidates"][0]["content"]["parts"]
            raw = "".join(part.get("text", "") for part in parts).strip()
            translations = json.loads(self._strip_json_fence(raw))
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TranslationError("Gemini returned an invalid translation response") from exc

        if (
            not isinstance(translations, list)
            or len(translations) != len(texts)
            or not all(isinstance(item, str) and item.strip() for item in translations)
        ):
            raise TranslationError(
                "Gemini returned a different number of translations than requested"
            )
        return translations

    @staticmethod
    def _strip_json_fence(text: str) -> str:
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            return "\n".join(lines[1:-1]).strip()
        return text

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
            return str(body.get("error", {}).get("message", "request rejected"))
        except (ValueError, TypeError, AttributeError):
            return "request rejected"
