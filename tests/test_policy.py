"""Decision-matrix coverage for the verification policy gates.

The baseline suite only exercised the security-gate branch of ``Policy.evaluate``.
These tests cover the remaining gates so that every user-facing decision
(``pass``, ``review``, ``blocked``, ``skipped``) has deterministic evidence:

- file-count gate -> BLOCKED
- churn gate -> REVIEW
- generic check failure -> BLOCKED
- generic check review -> REVIEW
- all-skipped checks -> PASS (no failure signal)
- security-gate override (block_on_security_failure=False)
"""

from __future__ import annotations

from proofsmith.models import ChangedFile, CheckResult, CheckStatus
from proofsmith.policy import Policy


def make_file(path: str = "src/app.py", additions: int = 1, deletions: int = 0) -> ChangedFile:
    return ChangedFile(path, additions, deletions)


def make_check(
    check_id: str = "unit",
    status: CheckStatus = CheckStatus.PASS,
    evidence: tuple[str, ...] = ("ok",),
) -> CheckResult:
    return CheckResult(check_id, check_id.title(), status, status.value, evidence=evidence)


def test_policy_blocks_when_file_count_exceeds_limit() -> None:
    files = tuple(make_file(f"src/part{i}.py") for i in range(251))
    status, reason = Policy().evaluate(files, ())
    assert status is CheckStatus.BLOCKED
    assert reason == f"change touches {len(files)} files; policy limit is 250"


def test_policy_passes_at_exactly_the_file_limit() -> None:
    files = tuple(make_file(f"src/part{i}.py") for i in range(250))
    status, reason = Policy().evaluate(files, (make_check(),))
    assert status is CheckStatus.PASS
    assert reason == "all policy gates passed"


def test_policy_reviews_high_churn_changes() -> None:
    files = (make_file("src/big.py", additions=4000, deletions=1001),)
    status, reason = Policy().evaluate(files, (make_check(),))
    assert status is CheckStatus.REVIEW
    assert reason == "change churn is 5001; review threshold is 5000"


def test_policy_passes_at_exactly_the_churn_limit() -> None:
    files = (make_file("src/big.py", additions=3000, deletions=2000),)
    status, reason = Policy().evaluate(files, (make_check(),))
    assert status is CheckStatus.PASS
    assert reason == "all policy gates passed"


def test_policy_blocks_generic_check_failure() -> None:
    checks = (make_check(check_id="unit", status=CheckStatus.BLOCKED),)
    status, reason = Policy().evaluate((make_file(),), checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"


def test_policy_reviews_when_any_check_needs_review() -> None:
    checks = (make_check(check_id="style", status=CheckStatus.REVIEW),)
    status, reason = Policy().evaluate((make_file(),), checks)
    assert status is CheckStatus.REVIEW
    assert reason == "one or more checks require human review"


def test_policy_blocks_takes_precedence_over_review() -> None:
    checks = (
        make_check(check_id="style", status=CheckStatus.REVIEW),
        make_check(check_id="unit", status=CheckStatus.BLOCKED),
    )
    status, reason = Policy().evaluate((make_file(),), checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"


def test_policy_all_skipped_checks_pass() -> None:
    checks = (make_check(check_id="lint", status=CheckStatus.SKIPPED),)
    status, reason = Policy().evaluate((make_file(),), checks)
    assert status is CheckStatus.PASS
    assert reason == "all policy gates passed"


def test_policy_passes_without_evidence_requirement() -> None:
    checks = (
        CheckResult("unit", "Unit tests", CheckStatus.PASS, "passed", evidence=()),
    )
    policy = Policy(require_evidence_for_pass=False)
    status, reason = policy.evaluate((make_file(),), checks)
    assert status is CheckStatus.PASS
    assert reason == "all policy gates passed"


def test_policy_security_override_allows_security_failure_review() -> None:
    checks = (
        CheckResult(
            "dependency-audit",
            "Dependency audit",
            CheckStatus.BLOCKED,
            "vulnerable",
            evidence=("pkg x CVE-1",),
        ),
    )
    policy = Policy(block_on_security_failure=False)
    status, reason = policy.evaluate((make_file(),), checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"


def test_policy_security_gate_ignores_non_blocked_results() -> None:
    checks = (
        CheckResult("secret-scan", "Secret scan", CheckStatus.REVIEW, "suspicious"),
    )
    status, reason = Policy().evaluate((make_file(),), checks)
    assert status is CheckStatus.REVIEW
    assert reason == "one or more checks require human review"


def test_policy_blocked_check_without_security_scope_is_blocked_directly() -> None:
    checks = (make_check(check_id="integration", status=CheckStatus.BLOCKED),)
    status, reason = Policy().evaluate((make_file(),), checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"
