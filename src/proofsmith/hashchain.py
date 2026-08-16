"""Canonical serialization and tamper-evident hash chaining."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value)
    return hashlib.sha256(payload).hexdigest()


def bundle_hash(bundle_without_hash: dict[str, Any]) -> str:
    return sha256(bundle_without_hash)


def verify_chain(bundles: list[dict[str, Any]]) -> tuple[bool, str]:
    previous: str | None = None
    for index, bundle in enumerate(bundles):
        if bundle.get("previous_hash") != previous:
            return (
                False,
                f"bundle {index} points to {bundle.get('previous_hash')!r}, expected {previous!r}",
            )
        actual = bundle.get("content_hash")
        unsigned = {key: value for key, value in bundle.items() if key != "content_hash"}
        if actual != bundle_hash(unsigned):
            return False, f"bundle {index} has an invalid content_hash"
        previous = actual
    return True, "chain verified"
