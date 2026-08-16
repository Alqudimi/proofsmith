"""Conservative redaction for evidence payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret|password)(\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"\b(?:sk|ghp|xoxb|AKIA)[A-Za-z0-9_\-]{12,}\b"),
)


def redact_text(value: str) -> str:
    result = value
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 3:
            result = pattern.sub(
                lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", result
            )
        else:
            result = pattern.sub("[REDACTED]", result)
    return result


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {str(key): redact(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact(item) for item in value]
    return value
