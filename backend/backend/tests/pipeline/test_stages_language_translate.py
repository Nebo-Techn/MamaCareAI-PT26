"""
Tests for the language detection and translation stages.

**Owner: Dev B** (see the Sprint 1 split in `docs/PIPELINE_BACKLOG.md`).
Nobody else edits this file during Sprint 1.

The stage template-method tests (retries, duplicate delivery, dead-lettering)
are NOT repeated here — they live once in
`test_stages_ingest_extract.py`, owned by Dev A. Test only what is specific to
these two stages: their routing decisions.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (Dev B): implement these. Every one uses build_test_container().
#
# === detect_language stage ===
#
# This stage is pure routing over a tiny interface, so a fake detector covers
# every branch with no network and no model download. All four branches below
# are cheap — there is no excuse for any of them being missing.
#
# def test_low_confidence_routes_to_human_confirmation():
#     Confidence below threshold -> NEEDS_LANGUAGE_CONFIRMATION, next_stage None.
#     Assert the alternatives are stored, so the human picks from a list rather
#     than typing a guess.
#
# def test_already_swahili_skips_translation():
#     Detected "sw" -> LANGUAGE_DETECTED, next stage "store".
#     Translation is bypassed entirely (PDF 3.4, first bullet) — but review is
#     NOT. Assert it still reaches the review queue.
#
# def test_other_language_routes_to_translation():
#     Detected "en" -> LANGUAGE_DETECTED, next stage "translate".
#
# def test_human_confirmed_language_is_not_overwritten():
#     A resource carrying a "language_confirmed_by" marker keeps its language;
#     the detector must not overwrite a human decision with a model's guess.
#
# === translate stage ===
#
# def test_creates_machine_version_one_with_engine_recorded():
#     author_kind=MACHINE, version_number=1, engine name stored — the only way
#     to answer "did quality change when we switched engines?" later.
#
# def test_rerun_does_not_create_a_second_machine_version():
#     Idempotency, and this one costs real money if it is wrong.
#
# def test_length_mismatch_from_translator_raises():
#     Fake translator returns fewer results than inputs. Must RAISE, not
#     silently mis-align every block after the gap.
#
# def test_block_structure_survives_translation():
#     Headings are still headings, `order` is preserved. The side-by-side
#     review UI depends on this.
# ---------------------------------------------------------------------------
