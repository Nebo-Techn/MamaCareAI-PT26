"""
Tests for the stage template method, plus the ingest and extract stages.

**Owner: Dev A** (see the Sprint 1 split in `docs/PIPELINE_BACKLOG.md`).
Nobody else edits this file during Sprint 1 — that is what keeps four people
working in parallel without a daily merge conflict.

The template-method tests live here because Dev A owns `stages/base.py`. They
are written ONCE and cover behaviour every stage inherits, so the other two
stage test files do not repeat them.

WHAT TO TEST IN A STAGE: routing decisions and side effects.
  - Did it end in the right status?
  - Did it publish the right next job?
  - Did it call the ports it should have?

WHAT NOT TO TEST HERE: whether PyMuPDF parses a PDF correctly. That is the
adapter's business, and testing it here means these tests need real files and
get slow — at which point people stop running them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (Dev A): implement these. Every one uses build_test_container().
#
# === The template method (stages/base.py) — test ONCE, applies to all stages ===
#
# def test_duplicate_delivery_is_a_no_op():
#     Run a job whose resource has already advanced past `accepts`.
#     Assert: nothing changes, NO exception, nothing dead-lettered.
#     THE MOST IMPORTANT TEST IN THE SUITE — at-least-once delivery means this
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
# === ingest stage ===
#
# def test_duplicate_hash_skips_fetching():
#     -> DUPLICATE, terminal, and the fetcher was never called.
#
# def test_successful_ingest_stores_raw_bytes_and_queues_extract():
#     -> FETCHED, bytes in the object store, "extract" job published.
#
# def test_rerun_with_existing_raw_key_does_not_refetch():
#     Idempotency: re-delivery must not hit the source again.
#
# def test_video_with_captions_records_them_in_metadata():
#     So the extract stage can skip ASR entirely.
#
# === extract stage ===
#
# def test_registry_picks_text_extractor_when_it_can_handle_payload():
#
# def test_falls_back_to_ocr_when_text_extractor_declines():
#     The fallback chain — the reason there are no if-statements in the stage.
#
# def test_output_below_min_chars_raises_extraction_error():
#     Garbage caught here never reaches an MT bill or a reviewer's queue.
# ---------------------------------------------------------------------------
