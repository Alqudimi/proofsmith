"""Adapters for deterministic Git change metadata."""

from __future__ import annotations

from pathlib import PurePosixPath

from .models import ChangedFile


class GitDiffError(ValueError):
    """Raised when Git numstat input cannot be parsed safely."""


def _safe_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path or "\x00" in path:
        raise GitDiffError("Git diff contains an empty or NUL-delimited path")
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise GitDiffError(f"unsafe changed path: {path!r}")
    return path


def parse_numstat(text: str) -> tuple[ChangedFile, ...]:
    """Parse `git diff --numstat` output without executing Git or shell commands.

    Git emits `-\t-\tpath` for binary files. Binary churn is represented as zero
    additions/deletions because a byte count is not a meaningful line metric.
    """
    files: list[ChangedFile] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t", 2)
        if len(parts) != 3:
            raise GitDiffError(
                f"invalid numstat line {line_number}: expected 3 tab-separated fields"
            )
        additions_raw, deletions_raw, raw_path = parts
        if additions_raw == "-" and deletions_raw == "-":
            additions = deletions = 0
        else:
            try:
                additions = int(additions_raw)
                deletions = int(deletions_raw)
            except ValueError as error:
                raise GitDiffError(f"invalid line counts on line {line_number}") from error
            if additions < 0 or deletions < 0:
                raise GitDiffError(f"negative line count on line {line_number}")
        files.append(
            ChangedFile(path=_safe_path(raw_path), additions=additions, deletions=deletions)
        )
    return tuple(files)
