"""Coverage for aggregate bundle status derivation edge cases.

The baseline suite never exercised the ``SKIPPED``-only or ``REVIEW``-only
branches of ``EvidenceBundle.now``, so these tests pin down the derived
``final_status`` for every composition of check results.
"""

from __future__ import annotations

from proofsmith.bundle import create_bundle
from proofsmith.models import (
    ChangedFile,
    CheckResult,
    CheckStatus,
    EvidenceBundle,
    VerificationRequest,
)


def make_request(checks: tuple[str, ...] = ("unit",)) -> VerificationRequest:
    return VerificationRequest(
        revision="rev-1",
        changed_files=(ChangedFile("src/app.py", 1, 0),),
        checks=checks,
    )


def make_check(check_id: str = "unit", status: CheckStatus = CheckStatus.PASS) -> CheckResult:
    return CheckResult(check_id, check_id.title(), status, status.value, evidence=("ok",))


def test_all_skipped_checks_derive_skipped_status() -> None:
    request = make_request(("lint",))
    checks = (make_check("lint", CheckStatus.SKIPPED),)
    bundle = EvidenceBundle.now(
        bundle_id="b-1",
        request=request,
        checks=checks,
        content_hash="hash",
    )
    assert bundle.final_status is CheckStatus.SKIPPED


def test_blocked_check_derives_blocked_status_even_with_skipped_others() -> None:
    request = make_request(("unit", "lint"))
    checks = (
        make_check("unit", CheckStatus.BLOCKED),
        make_check("lint", CheckStatus.SKIPPED),
    )
    bundle = create_bundle(request, checks)
    assert bundle.final_status is CheckStatus.BLOCKED


def test_review_check_derives_review_status() -> None:
    request = make_request(("unit",))
    checks = (make_check("unit", CheckStatus.REVIEW),)
    bundle = create_bundle(request, checks)
    assert bundle.final_status is CheckStatus.REVIEW


def test_no_checks_derive_pass_status() -> None:
    request = make_request(())
    bundle = create_bundle(request, ())
    assert bundle.final_status is CheckStatus.PASS


def test_bundle_to_dict_is_schema_versioned() -> None:
    bundle = EvidenceBundle.now(
        bundle_id="b-1",
        request=make_request(),
        checks=(make_check(),),
        content_hash="abc",
    )
    payload = bundle.to_dict()
    assert payload["schema_version"] == "proofsmith/v1"
    assert payload["bundle_id"] == "b-1"
    assert payload["final_status"] == "pass"


def test_bundle_preserves_previous_hash_in_chain() -> None:
    bundle = EvidenceBundle.now(
        bundle_id="b-2",
        request=make_request(),
        checks=(make_check(),),
        content_hash="def",
        previous_hash="abc",
    )
    assert bundle.previous_hash == "abc"
