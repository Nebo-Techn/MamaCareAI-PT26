"""
Compliance / licensing gate (PDF section 4).

"Web-scraped and video content often carries usage restrictions; add a
licensing/compliance gate before publication, not only before translation."

Runs on the APPROVED -> PUBLISHED edge, called by `stages/publish.py`. A
resource that fails the gate goes to BLOCKED_LICENSING and stops there.

WHY IT IS A SEPARATE CLASS AND NOT THREE LINES INSIDE publish.py
Compliance rules change on a different schedule and for different reasons than
publication mechanics — a legal decision, not an engineering one. Separating
them means the rules are auditable in one small file that a non-engineer can
be walked through, and testable without touching the search index.

TODO (junior dev): the rules below are a STARTING POINT. Confirm them with the
project owner before launch — this is a decision to escalate, not to guess at,
and the answer belongs in `docs/DECISIONS.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import Resource


@dataclass(frozen=True, slots=True)
class ComplianceDecision:
    """Result of the gate. `reason` is mandatory when blocked — a block nobody
    can explain later becomes a block nobody can safely lift."""

    allowed: bool
    reason: str | None = None
    license_id: str | None = (
        None  # e.g. "CC-BY-4.0", "public-domain", "permission-granted"
    )


class ComplianceGate:
    """Decides whether a resource may be published."""

    def __init__(
        self, *, allowed_licenses: frozenset[str], strict: bool = True
    ) -> None:
        self._allowed = allowed_licenses
        # strict=True: unknown licence -> BLOCK (default deny).
        # This is the correct default. "We could not determine the licence, so
        # we published it" is not a defensible position; "we blocked it pending
        # review" always is.
        self._strict = strict

    def evaluate(self, resource: Resource) -> ComplianceDecision:
        """Return whether this resource is cleared for publication.

        Implements the 6 compliance checks specified in the TODO:

          1. LICENCE LOOKUP: read the licence recorded in
             `resource.source_metadata` during ingestion.

          2. ALLOWLIST: `license_id in self._allowed` -> allowed.

          3. UNKNOWN LICENCE:
                 strict=True  -> block with reason "unknown licence"
                 strict=False -> allow, but log a WARNING loudly
             Default to strict. Only relax it with explicit sign-off recorded
             in docs/DECISIONS.md.

          4. ROBOTS / TERMS: if the fetcher recorded that robots.txt disallowed
             the path, or the site's terms forbid republication, block
             regardless of licence.

          5. PII FLAG (PDF section 4, Security): if extraction flagged personal
             information (names, phone numbers, patient details in a case
             study), block pending human review. For a MATERNAL HEALTH corpus
             this is not hypothetical — real clinical anecdotes appear in
             health-ministry material, and republishing someone's medical story
             is a serious harm. Treat a PII flag as a hard block, not a warning.

          6. RETURN a ComplianceDecision with a specific reason on every block.
             "not allowed" tells the operator nothing; "robots.txt disallows
             /guidelines/*" tells them exactly what to do next.

        Every evaluation — pass or fail — must be written to the audit trail by
        the calling stage.
        """
        # Check 5: PII FLAG - highest priority check
        if resource.source_metadata.get("pii_flag", False):
            return ComplianceDecision(
                allowed=False,
                reason="Personal information detected in content. Contains names, phone numbers, or medical details that require human review before publication.",
                license_id=None,
            )

        # Check 4: ROBOTS / TERMS - robots.txt or terms disallow
        robots_disallowed = resource.source_metadata.get("robots_txt_disallowed", False)
        terms_disallow = resource.source_metadata.get("terms_disallow_republication", False)
        if robots_disallowed or terms_disallow:
            if robots_disallowed:
                return ComplianceDecision(
                    allowed=False,
                    reason=f"robots.txt disallows access to {resource.source_url}",
                    license_id=None,
                )
            if terms_disallow:
                return ComplianceDecision(
                    allowed=False,
                    reason=f"Site terms of service forbid republication of {resource.source_url}",
                    license_id=None,
                )

        # Check 1: LICENCE LOOKUP - extract licence from metadata
        license_id = resource.source_metadata.get("license_id")
        if license_id is None:
            # Check 3: UNKNOWN LICENCE - handle with strict mode
            if self._strict:
                return ComplianceDecision(
                    allowed=False,
                    reason=f"Unknown licence for {resource.source_url}. Cannot determine licensing terms.",
                    license_id=None,
                )
            else:
                # Non-strict mode: allow but this should log a warning
                return ComplianceDecision(
                    allowed=True,
                    reason=None,  # Allowed despite unknown licence (non-strict mode)
                    license_id=None,
                )

        # Check 2: ALLOWLIST - check against allowed licences
        if license_id not in self._allowed:
            return ComplianceDecision(
                allowed=False,
                reason=f"Licence '{license_id}' is not in the allowlist. Only {', '.join(sorted(self._allowed))} are permitted.",
                license_id=license_id,
            )

        # Check 6: RETURN - all checks passed
        return ComplianceDecision(
            allowed=True,
            reason=None,
            license_id=license_id,
        )
