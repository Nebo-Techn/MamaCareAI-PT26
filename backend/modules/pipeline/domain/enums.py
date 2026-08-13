"""
Domain enums — the fixed vocabulary of the pipeline.

WHY THESE ARE ENUMS AND NOT STRINGS
A bare string status ("in_review") is a typo waiting to happen and gives you
no autocomplete, no exhaustiveness checking, and no single place to see every
legal value. Every status/type in this pipeline is an enum. If you need a new
value, add it here — never invent a magic string at a call site.

TODO (junior dev):
  [ ] Nothing to implement here yet — this file is complete as a definition.
      Extend it only when a genuinely new source type or state appears.
  [ ] If you add a ResourceStatus value, you MUST also add its allowed
      transitions in `state_machine.py`, or the pipeline will refuse to enter it.
"""

from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """Where a resource came from.

    Drives which Fetcher and which Extractor the registry picks
    (see `pipeline/registry.py`). Adding a source type here should require
    writing two new adapters — and editing zero existing stages.
    That is the Open/Closed Principle in practice.
    """

    WEB = "web"
    VIDEO = "video"
    PDF = "pdf"


class ResourceStatus(str, Enum):
    """The lifecycle state of one resource inside the pipeline.

    This is the single source of truth for "where is this document right now".
    Every stage reads it, updates it, and refuses to run if the resource is in
    a state it does not handle.

    Legal transitions live in `state_machine.py` — this enum only lists the
    states, not the arrows between them.
    """

    # --- Stage 1: ingestion ---
    SUBMITTED = "submitted"                 # job accepted, nothing fetched yet
    DUPLICATE = "duplicate"                  # dedup hit; terminal, no reprocessing
    FETCHED = "fetched"                      # raw bytes are in object storage

    # --- Stage 2: extraction & normalization ---
    EXTRACTED = "extracted"                  # normalized text exists

    # --- Stage 3: language detection ---
    LANGUAGE_DETECTED = "language_detected"
    NEEDS_LANGUAGE_CONFIRMATION = "needs_language_confirmation"  # low confidence -> human

    # --- Stage 4: translation ---
    TRANSLATED = "translated"                # machine translation output exists

    # --- Stage 5: storage ---
    STORED = "stored"                        # indexed + versioned, ready for review

    # --- Stage 6: human review ---
    IN_REVIEW = "in_review"
    NEEDS_EDIT = "needs_edit"
    EDITED = "edited"
    APPROVED = "approved"

    # --- Stage 7: published ---
    PUBLISHED = "published"

    # --- Off-happy-path ---
    BLOCKED_LICENSING = "blocked_licensing"  # compliance gate said no
    FAILED = "failed"                        # retries exhausted; in the dead-letter queue


class ReviewDecision(str, Enum):
    """What a human reviewer decided about a machine translation."""

    APPROVE = "approve"          # MT output is good as-is
    NEEDS_EDIT = "needs_edit"    # requires human correction before approval
    REJECT = "reject"            # unusable source/translation; do not publish


class VersionAuthorKind(str, Enum):
    """Who produced a given version of the translated content.

    Needed for the feedback loop (PDF 3.6): we can only mine MT-vs-human diffs
    as training signal if we can tell the two apart.
    """

    MACHINE = "machine"
    HUMAN = "human"


class JobStatus(str, Enum):
    """Delivery state of one unit of work on the queue."""

    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    DONE = "done"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"
