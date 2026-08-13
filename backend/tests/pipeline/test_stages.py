"""
Tests for the seven pipeline stages, using fakes.

WHAT TO TEST IN A STAGE: routing decisions and side effects.
  - Did it end in the right status?
  - Did it publish the right next job?
  - Did it call the ports it should have?

WHAT NOT TO TEST HERE: whether PyMuPDF parses a PDF correctly. That is the
adapter's business, and testing it here means the stage tests need real files
and get slow — at which point people stop running them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (junior dev): implement these. Every one uses build_test_container().
#
# --- The template method (stages/base.py) — test these ONCE, they apply to all
#
# def test_duplicate_delivery_is_a_no_op():
#     Run a job whose resource has already advanced past `accepts`.
#     Assert: nothing changes, NO exception, nothing dead-lettered.
#     THE MOST IMPORTANT TEST IN THIS FILE — at-least-once delivery means this
#     path runs in production regularly.
#
# def test_retryable_error_is_republished_with_backoff():
#     Fake fetcher raises FetchError. Assert the job is back on the queue with
#     not_before set, and NOT in the dead-letter queue.
#
# def test_permanent_error_goes_straight_to_dead_letter():
#     Fake extractor raises ExtractionError. Assert: dead-lettered immediately,
#     NOT retried, resource is FAILED. Retrying a permanent error five times
#     just multiplies the noise.
#
# def test_attempts_are_capped():
#     Always-failing retryable error -> dead-lettered after max_attempts.
#
# def test_next_job_is_published_only_after_the_state_change_is_saved():
#     Ordering matters (see stages/base.py step 7). Use a repository fake that
#     records call order.
#
# --- Per stage ---
#
# ingest:
#   [ ] duplicate hash -> DUPLICATE, no fetch attempted
#   [ ] success -> FETCHED, bytes in the object store, "extract" published
#   [ ] re-running with raw_object_key already set does NOT re-fetch
#   [ ] video with existing captions records them in metadata (skips ASR)
#
# extract:
#   [ ] registry picks the text-layer extractor when it can handle the payload
#   [ ] falls back to OCR when the text extractor declines  <- the fallback chain
#   [ ] output below min_extracted_chars raises ExtractionError
#
# detect_language:
#   [ ] confidence below threshold -> NEEDS_LANGUAGE_CONFIRMATION, next_stage None
#   [ ] detected "sw" -> LANGUAGE_DETECTED -> "store" (translation skipped)
#   [ ] detected "en" -> LANGUAGE_DETECTED -> "translate"
#   [ ] a human-confirmed language is NOT overwritten by the detector
#
# translate:
#   [ ] creates version 1 with author_kind=MACHINE and the engine recorded
#   [ ] re-running does NOT create a second machine version (costs money)
#   [ ] a length mismatch from the translator raises instead of mis-aligning
#   [ ] block structure survives: headings still headings, order preserved
#
# store:
#   [ ] indexes the content and creates exactly one review assignment
#   [ ] the already-Swahili path (no MT version) still indexes correctly
#       <- easy to miss; it silently breaks Swahili-native sources
#
# review:
#   [ ] STORED -> IN_REVIEW with next_stage None (waits for a human)
#
# publish:
#   [ ] compliance failure -> BLOCKED_LICENSING, nothing indexed
#   [ ] publishes the LATEST version, not version 1
#       <- guards against silently discarding every human edit
#   [ ] writes an audit event naming the approver
# ---------------------------------------------------------------------------
