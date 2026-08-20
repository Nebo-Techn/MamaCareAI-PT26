"""
Feedback loop — mining MT-vs-human diffs as training signal (PDF 3.6).

"Diffs between MT output and human edits are valuable training signal — feed
them back periodically to fine-tune or prompt-tune the translation step, so
review effort compounds instead of repeating indefinitely."

This is the highest-leverage file in the pipeline and the easiest to skip.
Without it, reviewers fix the same MT mistake every week forever. With it,
every correction improves the next batch. Build it once review has produced a
few hundred edits — not before (there is nothing to learn from yet), and not
much later (you are burning reviewer time the whole time it does not exist).

BUILT ON THE APPEND-ONLY VERSION HISTORY
This entire file is only possible because a human edit creates version N+1
instead of overwriting version 1. That is why `VersionRepository` has no update
method. If someone ever "optimizes" that away, this capability dies with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..ports.repositories import ResourceRepository, VersionRepository


@dataclass(frozen=True, slots=True)
class EditPair:
    """One training example: what the machine said, what the human corrected it to."""

    resource_id: str
    source_text: str
    machine_translation: str
    human_translation: str
    source_language: str
    engine: str                  # which MT engine produced the machine version
    edit_distance: float         # 0.0 = untouched, 1.0 = completely rewritten
    edited_at: datetime


class FeedbackExporter:
    """Extracts MT-vs-human edit pairs for fine-tuning and quality analysis."""

    def __init__(
        self, *, resources: ResourceRepository, versions: VersionRepository
    ) -> None:
        self._resources = resources
        self._versions = versions

    def collect_edit_pairs(
        self, *, since: datetime, min_edit_distance: float = 0.05
    ) -> list[EditPair]:
        """Gather MT/human pairs where a human actually changed something.

        TODO (junior dev):
          [ ] For each resource with a human version: fetch version 1 (machine)
              and the latest human version, and align their units by `order`.
              This is exactly why `TranslationUnit.order` exists.
          [ ] Compute normalized edit distance per unit (difflib ratio is fine
              to start; do not reach for a library until it is a bottleneck).
          [ ] SKIP near-identical pairs (< min_edit_distance). Training on
              "the human changed one comma" teaches the model nothing and
              dilutes the real signal.
          [ ] ALSO skip pairs where the human rewrote everything (> ~0.95) —
              those usually mean the SOURCE was bad, not the translation, and
              they will teach the model the wrong lesson.
          [ ] Return pairs, newest first.

        PRIVACY: these pairs may contain health content and reviewer
        identities. Do not include reviewer_id in an export destined for a
        third-party fine-tuning service. Aggregate, do not attribute.
        """
        raise NotImplementedError

    def export_jsonl(self, pairs: list[EditPair], destination: Path) -> int:
        """Write pairs as JSONL for fine-tuning. Returns the number written.

        TODO:
          [ ] One JSON object per line: {"source": ..., "mt": ..., "target": ...}.
          [ ] UTF-8, `ensure_ascii=False` — Swahili text must stay readable in
              the file, not turn into a wall of \\uXXXX escapes.
          [ ] Write to a temp file and rename into place, so a crashed export
              never leaves a half-written file that looks complete.
        """
        raise NotImplementedError

    def quality_report(self, *, since: datetime) -> dict[str, object]:
        """Aggregate stats on how much humans are correcting the MT engine.

        TODO: report per engine and per source language —
              - number of reviewed documents
              - % approved with no edit  <- the headline MT quality number
              - mean edit distance
              - the worst-scoring source languages

        THIS IS THE NUMBER TO PUT IN THE WEEK 4 AND WEEK 8 PRESENTATIONS.
        "% approved with no edit, trending up" is a real, defensible quality
        claim backed by human judgement. It is far stronger evidence than any
        automatic MT score, and it comes free from work the reviewers are
        already doing.
        """
        raise NotImplementedError
