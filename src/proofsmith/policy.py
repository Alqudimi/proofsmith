"""Policy evaluation for verification results."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ChangedFile, CheckResult, CheckStatus


@dataclass(frozen=True, slots=True)
class Policy:
    name: str = "default"
    max_changed_files: int = 250
    max_churn: int = 5000
    block_on_security_failure: bool = True
    require_evidence_for_pass: bool = True

    def evaluate(
        self, files: tuple[ChangedFile, ...], checks: tuple[CheckResult, ...]
    ) -> tuple[CheckStatus, str]:
        churn = sum(item.churn for item in files)
        if len(files) > self.max_changed_files:
            return (
                CheckStatus.BLOCKED,
                f"change touches {len(files)} files; policy limit is {self.max_changed_files}",
            )
        if churn > self.max_churn:
            return (
                CheckStatus.REVIEW,
                f"change churn is {churn}; review threshold is {self.max_churn}",
            )
        if not checks:
            return CheckStatus.SKIPPED, "no checks were provided; nothing to evaluate"
        security_failures = [
            check
            for check in checks
            if check.check_id in {"secret-scan", "dependency-audit"}
            and check.status is CheckStatus.BLOCKED
        ]
        if security_failures and self.block_on_security_failure:
            return CheckStatus.BLOCKED, "security gate failed"
        if any(check.status is CheckStatus.BLOCKED for check in checks):
            return CheckStatus.BLOCKED, "one or more required checks failed"
        if any(check.status is CheckStatus.REVIEW for check in checks):
            return CheckStatus.REVIEW, "one or more checks require human review"
        actionable = [check for check in checks if check.status is not CheckStatus.SKIPPED]
        if not actionable:
            return CheckStatus.SKIPPED, "all checks were skipped; no evaluation was possible"
        if self.require_evidence_for_pass and any(not check.evidence for check in actionable):
            return CheckStatus.REVIEW, "passing checks must include evidence"
        return CheckStatus.PASS, "all policy gates passed"
