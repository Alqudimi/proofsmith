"""Deterministic change-impact planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from .models import ChangedFile


@dataclass(frozen=True, slots=True)
class ImpactPlan:
    checks: tuple[str, ...]
    reasons: dict[str, tuple[str, ...]]


_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("python", ("*.py", "pyproject.toml"), ("unit", "lint", "typecheck")),
    ("frontend", ("*.tsx", "*.ts", "*.css", "package.json"), ("frontend-build", "frontend-check")),
    ("workflow", (".github/workflows/*.yml", ".github/workflows/*.yaml"), ("workflow-lint",)),
    ("docs", ("*.md", "docs/*.md"), ("docs-links",)),
    (
        "security",
        (
            "SECURITY.md",
            "*.lock",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "poetry.lock",
            "Gemfile.lock",
            "composer.lock",
            "Cargo.lock",
            "go.sum",
            "uv.lock",
        ),
        ("secret-scan", "dependency-audit"),
    ),
)


def _matches(path: str, pattern: str) -> bool:
    return PurePosixPath(path).match(pattern)


def plan_for(files: tuple[ChangedFile, ...]) -> ImpactPlan:
    reasons: dict[str, list[str]] = {}
    for changed in files:
        for label, patterns, checks in _RULES:
            if any(_matches(changed.path, pattern) for pattern in patterns):
                for check in checks:
                    reasons.setdefault(check, []).append(f"{label}:{changed.path}")
    selected = tuple(sorted(reasons))
    return ImpactPlan(selected, {key: tuple(values) for key, values in sorted(reasons.items())})
