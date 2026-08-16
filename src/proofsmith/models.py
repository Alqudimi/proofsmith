"""Domain models for deterministic verification evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CheckStatus(StrEnum):
    PASS = "pass"
    REVIEW = "review"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ChangedFile:
    path: str
    additions: int
    deletions: int
    status: str = "modified"

    @property
    def churn(self) -> int:
        return self.additions + self.deletions


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_id: str
    title: str
    status: CheckStatus
    summary: str
    duration_ms: int = 0
    evidence: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    revision: str
    changed_files: tuple[ChangedFile, ...]
    checks: tuple[str, ...]
    policy_name: str = "default"
    source: str = "local"


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    schema_version: str
    bundle_id: str
    created_at: str
    request: VerificationRequest
    checks: tuple[CheckResult, ...]
    final_status: CheckStatus
    content_hash: str
    previous_hash: str | None = None

    @classmethod
    def now(
        cls,
        bundle_id: str,
        request: VerificationRequest,
        checks: tuple[CheckResult, ...],
        content_hash: str,
        previous_hash: str | None = None,
    ) -> EvidenceBundle:
        status = CheckStatus.PASS
        if any(check.status is CheckStatus.BLOCKED for check in checks):
            status = CheckStatus.BLOCKED
        elif any(check.status is CheckStatus.REVIEW for check in checks):
            status = CheckStatus.REVIEW
        elif checks and all(check.status is CheckStatus.SKIPPED for check in checks):
            status = CheckStatus.SKIPPED
        return cls(
            schema_version="proofsmith/v1",
            bundle_id=bundle_id,
            created_at=datetime.now(UTC).isoformat(),
            request=request,
            checks=checks,
            final_status=status,
            content_hash=content_hash,
            previous_hash=previous_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
