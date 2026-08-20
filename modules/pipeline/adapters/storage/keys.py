"""
Object storage key conventions.

WHY THIS IS A FILE AND NOT AN f-STRING AT THE CALL SITE
Storage keys are effectively permanent. Once ten thousand objects are written
under a naming scheme, changing it means a migration, not an edit. Defining the
scheme once, here, means it is reviewable now and greppable later.

THE SCHEME:

    raw/{yyyy}/{mm}/{resource_id}/original.{ext}    the fetched bytes
    raw/{yyyy}/{mm}/{resource_id}/audio.{ext}       extracted audio for ASR
    derived/{resource_id}/normalized.json           the NormalizedDocument

Design choices, each for a reason:
  - DATE PREFIX FIRST: makes lifecycle rules trivial ("move raw/2026/01/* to
    cold storage"). On S3 it also spreads writes across partitions instead of
    hot-spotting one.
  - RESOURCE_ID AS A DIRECTORY: everything about one resource is browsable in
    one place during debugging, which matters more often than you would think.
  - EXTENSION PRESERVED: so a human downloading the object can open it.
"""

from __future__ import annotations

from ...domain.models import Resource


def build_raw_key(resource: Resource, *, extension: str) -> str:
    """Key for the originally fetched bytes.

    TODO (junior dev):
      [ ] Return f"raw/{yyyy}/{mm}/{resource_id}/original.{extension}", using
          `resource.submitted_at` for the date — NOT `utcnow()`. A retry must
          produce the SAME key as the first attempt, or the retry writes a
          second copy of the same file and `exists()` never short-circuits.
          Deterministic keys are what make the ingest stage idempotent.
      [ ] Normalize the extension: lowercase, no leading dot, and validate it
          against a small allowlist so a hostile Content-Type cannot inject
          path separators into the key.
    """
    raise NotImplementedError


def build_audio_key(resource: Resource, *, extension: str) -> str:
    """Key for audio extracted from a video, for the ASR stage.

    TODO: same date/id prefix, filename "audio.{extension}". Keeping it beside
    the original means a debugging engineer finds both in one listing.
    """
    raise NotImplementedError


def build_normalized_key(resource_id: str) -> str:
    """Key for the serialized NormalizedDocument.

    TODO: f"derived/{resource_id}/normalized.json".

    NOTE: only needed if you store normalized documents in object storage
    rather than in the database. For MamaCare's volume the database is simpler
    and easier to query — prefer that, and treat this as a scaling escape hatch
    documented in docs/DECISIONS.md if documents ever get large enough to hurt.
    """
    raise NotImplementedError
