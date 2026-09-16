"""
Tests for the compliance gate (PIPE-29).

Tests all 6 compliance checks specified in the TODO:
1. LICENCE LOOKUP
2. ALLOWLIST
3. UNKNOWN LICENCE (strict mode)
4. ROBOTS / TERMS
5. PII FLAG
6. RETURN specific reasons

**Owner: Dev A**
"""

from __future__ import annotations

from modules.pipeline.domain.enums import ResourceStatus, SourceType
from modules.pipeline.domain.models import Resource
from modules.pipeline.services.compliance import ComplianceGate


def make_resource(**overrides) -> Resource:
    """Create a test resource with sensible defaults."""
    fields = {
        "resource_id": "r1",
        "source_type": SourceType.WEB,
        "source_url": "https://example.org/article",
        "status": ResourceStatus.APPROVED,
        "source_metadata": {},
    }
    fields.update(overrides)
    return Resource(**fields)


class TestComplianceGate:
    """Test the ComplianceGate implementation."""

    def test_licence_lookup_and_allowlist_allows_permitted_licence(self) -> None:
        """Test 1 & 2: LICENCE LOOKUP and ALLOWLIST allow permitted licences."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0", "public-domain"}), strict=True
        )
        resource = make_resource(
            source_metadata={"license_id": "CC-BY-4.0"}
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is True
        assert decision.reason is None
        assert decision.license_id == "CC-BY-4.0"

    def test_licence_lookup_and_allowlist_blocks_non_allowed_licence(self) -> None:
        """Test 1 & 2: LICENCE LOOKUP and ALLOWLIST block non-allowed licences."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0", "public-domain"}), strict=True
        )
        resource = make_resource(
            source_metadata={"license_id": "ALL-RIGHTS-RESERVED"}
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        assert "ALL-RIGHTS-RESERVED" in decision.reason
        assert "not in the allowlist" in decision.reason
        assert decision.license_id == "ALL-RIGHTS-RESERVED"

    def test_unknown_licence_strict_mode_blocks(self) -> None:
        """Test 3: UNKNOWN LICENCE blocks in strict mode."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )
        resource = make_resource(source_metadata={})  # No license_id

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        assert "Unknown licence" in decision.reason
        assert "Cannot determine licensing terms" in decision.reason
        assert decision.license_id is None

    def test_unknown_licence_non_strict_mode_allows(self) -> None:
        """Test 3: UNKNOWN LICENCE allows in non-strict mode."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=False
        )
        resource = make_resource(source_metadata={})  # No license_id

        decision = gate.evaluate(resource)

        assert decision.allowed is True
        assert decision.reason is None
        assert decision.license_id is None

    def test_robots_txt_disallowed_blocks(self) -> None:
        """Test 4: ROBOTS disallow blocks regardless of licence."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )
        resource = make_resource(
            source_metadata={
                "license_id": "CC-BY-4.0",
                "robots_txt_disallowed": True,
            }
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        assert "robots.txt disallows" in decision.reason
        assert decision.license_id is None

    def test_terms_disallow_republication_blocks(self) -> None:
        """Test 4: TERMS disallow blocks regardless of licence."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )
        resource = make_resource(
            source_metadata={
                "license_id": "CC-BY-4.0",
                "terms_disallow_republication": True,
            }
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        assert "terms of service forbid republication" in decision.reason
        assert decision.license_id is None

    def test_pii_flag_blocks_highest_priority(self) -> None:
        """Test 5: PII FLAG blocks even with valid licence."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )
        resource = make_resource(
            source_metadata={
                "license_id": "CC-BY-4.0",
                "pii_flag": True,
            }
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        assert "Personal information detected" in decision.reason
        assert "human review" in decision.reason
        assert decision.license_id is None

    def test_pii_flag_blocks_even_with_robots_allowed(self) -> None:
        """Test 5: PII FLAG blocks even when robots would allow."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )
        resource = make_resource(
            source_metadata={
                "license_id": "CC-BY-4.0",
                "robots_txt_disallowed": False,
                "pii_flag": True,
            }
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        assert "Personal information detected" in decision.reason

    def test_specific_reason_on_every_block(self) -> None:
        """Test 6: RETURN specific reason on every block."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )

        # Test unknown licence
        resource = make_resource(source_metadata={})
        decision = gate.evaluate(resource)
        assert decision.reason is not None
        assert len(decision.reason) > 10  # Specific, not generic

        # Test non-allowed licence
        resource = make_resource(source_metadata={"license_id": "PROPRIETARY"})
        decision = gate.evaluate(resource)
        assert decision.reason is not None
        assert "PROPRIETARY" in decision.reason

        # Test robots disallow
        resource = make_resource(
            source_metadata={"robots_txt_disallowed": True}
        )
        decision = gate.evaluate(resource)
        assert decision.reason is not None
        assert "robots.txt" in decision.reason

        # Test PII flag
        resource = make_resource(source_metadata={"pii_flag": True})
        decision = gate.evaluate(resource)
        assert decision.reason is not None
        assert "Personal information" in decision.reason

    def test_public_domain_allowed(self) -> None:
        """Test that public domain is allowed when in allowlist."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"public-domain"}), strict=True
        )
        resource = make_resource(source_metadata={"license_id": "public-domain"})

        decision = gate.evaluate(resource)

        assert decision.allowed is True
        assert decision.license_id == "public-domain"

    def test_permission_granted_allowed(self) -> None:
        """Test that permission-granted is allowed when in allowlist."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"permission-granted"}), strict=True
        )
        resource = make_resource(
            source_metadata={"license_id": "permission-granted"}
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is True
        assert decision.license_id == "permission-granted"

    def test_cc_by_sa_allowed(self) -> None:
        """Test that CC-BY-SA is allowed when in allowlist."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-SA-4.0"}), strict=True
        )
        resource = make_resource(source_metadata={"license_id": "CC-BY-SA-4.0"})

        decision = gate.evaluate(resource)

        assert decision.allowed is True
        assert decision.license_id == "CC-BY-SA-4.0"

    def test_case_sensitive_licence_check(self) -> None:
        """Test that licence checking is case-sensitive."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )
        resource = make_resource(source_metadata={"license_id": "cc-by-4.0"})

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        assert "cc-by-4.0" in decision.reason

    def test_multiple_robots_and_terms_flags(self) -> None:
        """Test handling of both robots and terms flags."""
        gate = ComplianceGate(
            allowed_licenses=frozenset({"CC-BY-4.0"}), strict=True
        )
        resource = make_resource(
            source_metadata={
                "license_id": "CC-BY-4.0",
                "robots_txt_disallowed": True,
                "terms_disallow_republication": True,
            }
        )

        decision = gate.evaluate(resource)

        assert decision.allowed is False
        # Should report robots.txt first (checked first in code)
        assert "robots.txt" in decision.reason