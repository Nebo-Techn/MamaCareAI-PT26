from __future__ import annotations

import re
from datetime import UTC

from ...domain.models import Resource

_ALLOWED_EXTENSIONS = frozenset(
    {
        "aac",
        "avi",
        "flac",
        "html",
        "htm",
        "jpeg",
        "jpg",
        "m4a",
        "m4v",
        "mp3",
        "mp4",
        "pdf",
        "png",
        "wav",
        "webm",
    }
)
_SAFE_SEGMENT = re.compile(r"[A-Za-z0-9_-]+\Z")


def _resource_prefix(resource: Resource) -> str:
    resource_id = _validate_segment(resource.resource_id, "resource_id")
    if resource.submitted_at.tzinfo is None:
        raise ValueError("submitted_at must be timezone-aware")
    submitted_at = resource.submitted_at.astimezone(UTC)
    return f"raw/{submitted_at:%Y}/{submitted_at:%m}/{resource_id}"


def _validate_segment(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or _SAFE_SEGMENT.fullmatch(value) is None:
        raise ValueError(f"{name} must be a safe single path segment")
    return value


def _normalize_extension(extension: str) -> str:
    if not isinstance(extension, str):
        raise TypeError("extension must be a string")
    normalized = extension.strip().lower().lstrip(".")
    if normalized not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported file extension: {extension!r}")
    return normalized


def build_raw_key(resource: Resource, *, extension: str) -> str:
    return f"{_resource_prefix(resource)}/original.{_normalize_extension(extension)}"


def build_audio_key(resource: Resource, *, extension: str) -> str:
    return f"{_resource_prefix(resource)}/audio.{_normalize_extension(extension)}"


def build_normalized_key(resource_id: str) -> str:
    resource_id = _validate_segment(resource_id, "resource_id")
    return f"derived/{resource_id}/normalized.json"
