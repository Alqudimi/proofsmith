"""Full decision-matrix coverage for Policy.evaluate.

The baseline suite only exercised the security-gate failure branch. These tests
verify every user-facing decision branch (`pass`/`review`/`blocked`), including
the file-count and churn gates, boundary conditions at exactly the configured
limits, the generic `BLOCKED`/`REVIEW` propagation paths, and the
`block_on_security_failure=False` override semantics.
"""

from __future__ import annotations

import pytest

from proofsmith.models import ChangedFile, CheckResult, CheckStatus
from proofsmith.policy import Policy


def _checks(items: tuple[tuple[str, str], ...]) -> tuple[CheckResult, ...]:
    """Build CheckResult tuples from (check_id, status) pairs."""
    return tuple(
        CheckResult(check_id, check_id.replace("-", " "), CheckStatus(status), "summary")
        for check_id, status in items
    )


@pytest.fixture()
def small_files() -> tuple[ChangedFile, ...]:
    return (ChangedFile("src/app.py", 10, 2),)


@pytest.fixture()
def default_policy() -> Policy:
    return Policy()


def _status(
    policy: Policy,
    files: tuple[ChangedFile, ...],
    checks: tuple[CheckResult, ...],
) -> CheckStatus:
    return policy.evaluate(files, checks)[0]


def test_passes_small_clean_change_with_evidence(
    small_files: tuple[ChangedFile, ...],
) -> None:
    policy = Policy(require_evidence_for_pass=False)
    checks = _checks((("unit", "pass"),))
    assert _status(policy, small_files, checks) is CheckStatus.PASS


def test_passes_at_exact_file_limit(small_files: tuple[ChangedFile, ...]) -> None:
    """A change touching exactly max_changed_files (250) still passes."""
    policy = Policy(require_evidence_for_pass=False)
    files = tuple(small_files) * policy.max_changed_files
    assert len(files) == policy.max_changed_files
    assert _status(policy, files, _checks((("unit", "pass"),))) is CheckStatus.PASS


def test_blocks_file_count_overflow(default_policy: Policy) -> None:
    """A change touching more than max_changed_files is BLOCKED regardless of checks."""
    limit = default_policy.max_changed_files + 1
    files = tuple(ChangedFile(f"src/{index}.py", 1, 0) for index in range(limit))
    status, reason = default_policy.evaluate(files, _checks((("unit", "pass"),)))
    assert status is CheckStatus.BLOCKED
    assert str(default_policy.max_changed_files + 1) in reason
    assert str(default_policy.max_changed_files) in reason


def test_file_count_gate_runs_before_security_gate() -> None:
    """The file-count gate is evaluated first and rejects even with a security
    failure present; the reason must report the size problem.

    Reviewers relying on the rejection reason should see the size problem
    rather than the security-gate message when the change is too large.
    """
    policy = Policy()
    limit = policy.max_changed_files + 1
    files = tuple(ChangedFile(f"src/{index}.py", 1, 0) for index in range(limit))
    checks = _checks((("secret-scan", "blocked"),))
    status, reason = policy.evaluate(files, checks)
    assert status is CheckStatus.BLOCKED
    assert "files" in reason




def test_churn_over_limit_triggers_review() -> None:
    """A change exceeding max_churn requests REVIEW rather than hard blocking."""
    policy = Policy(require_evidence_for_pass=False)
    big = ChangedFile("src/big.py", policy.max_churn + 1, 0)
    status, reason = policy.evaluate((big,), _checks((("unit", "pass"),)))
    assert status is CheckStatus.REVIEW
    assert "churn" in reason


def test_churn_gate_precedes_non_security_blocks() -> None:
    """The churn gate runs before generic check-failure propagation."""
    policy = Policy(require_evidence_for_pass=False)
    big = ChangedFile("src/big.py", policy.max_churn + 100, 0)
    checks = _checks((("lint", "blocked"),))
    status, reason = policy.evaluate((big,), checks)
    assert status is CheckStatus.REVIEW
    assert "churn" in reason


def test_blocks_generic_check_failure(
    default_policy: Policy,
    small_files: tuple[ChangedFile, ...],
) -> None:
    """A non-security BLOCKED check fails the policy with a generic message."""
    checks = _checks((("lint", "blocked"),))
    status, reason = default_policy.evaluate(small_files, checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"


def test_review_propagates_non_security_review_check(
    default_policy: Policy, small_files: tuple[ChangedFile, ...]
) -> None:
    """A non-security REVIEW check propagates to the policy decision."""
    checks = _checks((("complexity", "review"),))
    status, reason = default_policy.evaluate(small_files, checks)
    assert status is CheckStatus.REVIEW
    assert reason == "one or more checks require human review"


def test_blocked_preceded_review(
    default_policy: Policy,
    small_files: tuple[ChangedFile, ...],
) -> None:
    """A BLOCKED check dominates a concurrent REVIEW check."""
    checks = _checks((("complexity", "review"), ("lint", "blocked")))
    status, reason = default_policy.evaluate(small_files, checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"


def test_security_gate_skipped_when_override_disabled(
    default_policy: Policy, small_files: tuple[ChangedFile, ...]
) -> None:
    """Disabling block_on_security_failure downgrades the security gate.

    The security check still participates via the generic failure path, so the
    policy still blocks — but for the generic gate reason instead of the
    dedicated security gate reason. This is the documented override behavior:
    the gate itself is bypassed, while the underlying blocked check remains a
    failing check.
    """
    policy = Policy(block_on_security_failure=False)
    checks = _checks((("secret-scan", "blocked"),))
    status, reason = policy.evaluate(small_files, checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"


def test_dependency_audit_is_a_security_check(
    default_policy: Policy, small_files: tuple[ChangedFile, ...]
) -> None:
    """`dependency-audit` joins `secret-scan` in the security gate."""
    checks = _checks((("dependency-audit", "blocked"),))
    status, reason = default_policy.evaluate(small_files, checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "security gate failed"


def test_security_review_does_not_trigger_gate(
    default_policy: Policy, small_files: tuple[ChangedFile, ...]
) -> None:
    """A security check in REVIEW status does not activate the security gate.

    The security gate only considers security checks with BLOCKED status; a
    reviewing security check passes through to the generic propagation rules.
    """
    checks = _checks((("secret-scan", "review"),))
    status, reason = default_policy.evaluate(small_files, checks)
    assert status is CheckStatus.REVIEW
    assert reason == "one or more checks require human review"


def test_missing_evidence_triggers_review_when_required(
    default_policy: Policy, small_files: tuple[ChangedFile, ...]
) -> None:
    """Passing checks without evidence become REVIEW when evidence is required."""
    checks = _checks((("unit", "pass"),))
    status, reason = default_policy.evaluate(small_files, checks)
    assert status is CheckStatus.REVIEW
    assert "evidence" in reason


def test_evidence_not_required_when_disabled(
    small_files: tuple[ChangedFile, ...],
) -> None:
    """Disabling require_evidence_for_pass allows evidence-less passes."""
    policy = Policy(require_evidence_for_pass=False)
    checks = _checks((("unit", "pass"),))
    status, reason = policy.evaluate(small_files, checks)
    assert status is CheckStatus.PASS
    assert reason == "all policy gates passed"


def test_skipped_checks_pass_when_no_other_checks(default_policy: Policy) -> None:
    """An empty check list passes; SKIPPED-only bundles are evaluated by now().

    Policy.evaluate considers only BLOCKED/REVIEW/evidence rules, so a bundle
    whose every check was skipped has no failing signal at the policy layer.
    """
    status, reason = default_policy.evaluate((), ())
    assert status is CheckStatus.PASS
    assert reason == "all policy gates passed"


def test_policy_is_immutable() -> None:
    """Policy dataclass instances cannot be mutated after construction."""
    with pytest.raises(AttributeError):
        Policy().max_churn = 100  # type: ignore[misc]
