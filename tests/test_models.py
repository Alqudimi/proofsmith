"""Aggregate status derivation coverage for EvidenceBundle.now.

The baseline suite exercised only the `PASS` and (via policy) `REVIEW`
aggregates. These tests cover every status composition, including the
`SKIPPED`-only branch and the BLOCKED-over-REVIEW precedence rule.
"""

from __future__ import annotations

import pytest

from proofsmith.models import CheckResult, CheckStatus, EvidenceBundle, VerificationRequest


def _bundle(checks: tuple[CheckResult, ...]) -> EvidenceBundle:
    return EvidenceBundle.now(
        bundle_id="ps_test",
        request=VerificationRequest(
            revision="abc123",
            changed_files=(),
            checks=tuple(check.check_id for check in checks),
        ),
        checks=checks,
        content_hash="0" * 64,
    )


def _check(check_id: str, status: CheckStatus) -> CheckResult:
    return CheckResult(check_id, check_id, status, "summary")


def test_aggregate_pass() -> None:
    bundle = _bundle((_check("unit", CheckStatus.PASS),))
    assert bundle.final_status is CheckStatus.PASS


def test_aggregate_blocked_from_any_blocked_check() -> None:
    bundle = _bundle((_check("unit", CheckStatus.PASS), _check("lint", CheckStatus.BLOCKED)))
    assert bundle.final_status is CheckStatus.BLOCKED


def test_blocked_preceded_review() -> None:
    bundle = _bundle((_check("unit", CheckStatus.REVIEW), _check("lint", CheckStatus.BLOCKED)))
    assert bundle.final_status is CheckStatus.BLOCKED


def test_aggregate_review() -> None:
    bundle = _bundle((_check("complexity", CheckStatus.REVIEW),))
    assert bundle.final_status is CheckStatus.REVIEW


def test_review_over_pass() -> None:
    bundle = _bundle((_check("unit", CheckStatus.PASS), _check("complexity", CheckStatus.REVIEW)))
    assert bundle.final_status is CheckStatus.REVIEW


def test_aggregate_skipped_only() -> None:
    """All-skipped checks derive a SKIPPED aggregate status (models.py line 76)."""
    bundle = _bundle((_check("windows", CheckStatus.SKIPPED), _check("macos", CheckStatus.SKIPPED)))
    assert bundle.final_status is CheckStatus.SKIPPED


def test_empty_checks_derive_pass() -> None:
    bundle = _bundle(())
    assert bundle.final_status is CheckStatus.PASS


def test_status_value_matches_enum() -> None:
    bundle = _bundle((_check("unit", CheckStatus.BLOCKED),))
    assert bundle.final_status.value == "blocked"


def test_bundle_fields_are_frozen() -> None:
    bundle = _bundle(())
    with pytest.raises(AttributeError):
        bundle.final_status = CheckStatus.REVIEW  # type: ignore[misc]


def test_to_dict_includes_all_fields() -> None:
    bundle = _bundle((_check("unit", CheckStatus.PASS),))
    data = bundle.to_dict()
    assert data["schema_version"] == "proofsmith/v1"
    assert data["bundle_id"] == "ps_test"
    assert data["final_status"].value == "pass"
    assert isinstance(data["checks"], tuple)
    assert data["checks"][0]["check_id"] == "unit"
    assert data["checks"][0]["evidence"] == ()
