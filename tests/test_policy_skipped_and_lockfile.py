"""Contract coverage for the SKIPPED policy decision and lockfile security matching.

ProofSmith's domain models and documentation advertise four policy outcomes
(`pass`, `review`, `blocked`, `skipped`), but the policy layer previously could
not emit `skipped`: an empty check list or an all-skipped check list would
fall through to `pass`/`review` paths. These tests pin the corrected contract
so a future regression either passes or fails loudly.
"""

from __future__ import annotations

from proofsmith.impact import plan_for
from proofsmith.models import ChangedFile, CheckResult, CheckStatus
from proofsmith.policy import Policy


def _check(check_id: str, status: CheckStatus, evidence: tuple[str, ...] = ("ok",)) -> CheckResult:
    return CheckResult(check_id, check_id, status, status.value, evidence=evidence)


def test_empty_check_list_is_skipped() -> None:
    status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), ())
    assert status is CheckStatus.SKIPPED
    assert "no checks were provided" in reason


def test_all_skipped_checks_is_skipped() -> None:
    checks = (_check("lint", CheckStatus.SKIPPED, ()), _check("unit", CheckStatus.SKIPPED, ()))
    status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
    assert status is CheckStatus.SKIPPED
    assert "no evaluation was possible" in reason


def test_mixed_pass_with_missing_evidence_and_skipped_is_review() -> None:
    """Ephemeral evidence requirements still apply to actionable checks.

    A passing check without evidence must not become `pass` just because
    another check was skipped; skipping one check never excuses another.
    """
    checks = (_check("unit", CheckStatus.PASS, ()), _check("lint", CheckStatus.SKIPPED, ()))
    status, _ = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
    assert status is CheckStatus.REVIEW


def test_skipped_check_without_evidence_does_not_fail_evidence_gate() -> None:
    """Skipped checks carry no obligations; only actionable checks need evidence."""
    checks = (
        _check("unit", CheckStatus.PASS, ("2 passed",)),
        _check("lint", CheckStatus.SKIPPED, ()),
    )
    status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
    assert status is CheckStatus.PASS
    assert reason == "all policy gates passed"


def test_security_failure_blocks_even_when_checks_are_partly_skipped() -> None:
    checks = (
        _check("secret-scan", CheckStatus.BLOCKED, ("detected",)),
        _check("lint", CheckStatus.SKIPPED, ()),
    )
    status, reason = Policy().evaluate((ChangedFile("package-lock.json", 10, 0),), checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "security gate failed"


def test_non_security_blocked_check_blocks() -> None:
    """Any blocked check (not just security ones) fails the policy gate."""
    checks = (_check("unit", CheckStatus.BLOCKED, ("failed",)),)
    status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
    assert status is CheckStatus.BLOCKED
    assert reason == "one or more required checks failed"


def test_file_count_boundary_blocks_exactly_at_limit_plus_one() -> None:
    policy = Policy(max_changed_files=10)
    within = tuple(ChangedFile(f"src/f{i}.py", 1, 0) for i in range(10))
    beyond = (*within, ChangedFile("src/extra.py", 1, 0))
    ok_status, _ = policy.evaluate(within, (_check("unit", CheckStatus.PASS, ("ok",)),))
    assert ok_status is CheckStatus.PASS
    over_status, reason = policy.evaluate(beyond, (_check("unit", CheckStatus.PASS, ("ok",)),))
    assert over_status is CheckStatus.BLOCKED
    assert "11 files" in reason and "limit is 10" in reason


def test_churn_boundary_triggers_review() -> None:
    policy = Policy(max_churn=100)
    files = (ChangedFile("src/big.py", 60, 45),)
    status, reason = policy.evaluate(files, (_check("unit", CheckStatus.PASS, ("ok",)),))
    assert status is CheckStatus.REVIEW
    assert "105" in reason


def test_reviewable_check_outweighs_skipped_checks() -> None:
    checks = (
        _check("unit", CheckStatus.REVIEW, ("flaky",)),
        _check("lint", CheckStatus.SKIPPED, ()),
    )
    status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
    assert status is CheckStatus.REVIEW
    assert reason == "one or more checks require human review"


def test_lockfile_names_trigger_security_checks() -> None:
    lockfiles = (
        ChangedFile("package-lock.json", 50, 0),
        ChangedFile("pnpm-lock.yaml", 30, 0),
        ChangedFile("yarn.lock", 20, 0),
        ChangedFile("poetry.lock", 10, 0),
        ChangedFile("Gemfile.lock", 8, 0),
        ChangedFile("composer.lock", 5, 0),
        ChangedFile("Cargo.lock", 4, 0),
        ChangedFile("go.sum", 3, 0),
        ChangedFile("uv.lock", 2, 0),
    )
    plan = plan_for(lockfiles)
    assert "secret-scan" in plan.checks
    assert "dependency-audit" in plan.checks
    for item in lockfiles:
        assert any(item.path in value for value in plan.reasons["secret-scan"])


def test_nested_lockfile_also_matches() -> None:
    plan = plan_for((ChangedFile("packages/api/package-lock.json", 1, 0),))
    assert "secret-scan" in plan.checks
    assert any("packages/api/package-lock.json" in value for value in plan.reasons["secret-scan"])


def test_non_lockfile_yaml_does_not_match_security() -> None:
    """Regression: unrelated YAML (docs, guides) must never trigger security checks.

    Only files that are actually dependency manifests or lockfiles should pull
    in security checks; docs/guide.yml documents the project but is not one.
    """
    plan = plan_for((ChangedFile("docs/guide.yml", 4, 0),))
    assert "secret-scan" not in plan.checks
    assert "dependency-audit" not in plan.checks


def test_lockfile_plan_is_deterministic_with_stable_reasons() -> None:
    files = (
        ChangedFile("src/app.py", 1, 0),
        ChangedFile("package-lock.json", 1, 0),
    )
    plan = plan_for(files)
    assert plan.checks == tuple(sorted(plan.checks))
    assert "secret-scan" in plan.checks
    assert "unit" in plan.checks
    assert all(isinstance(value, tuple) for value in plan.reasons.values())
