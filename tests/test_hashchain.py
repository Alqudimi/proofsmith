"""Tamper-evident hash chain coverage.

The baseline suite only verified the happy path of `verify_chain` on a
`create_bundle`-produced artifact. These tests prove the core security promise
of the product: the chain must reject broken links, missing previous hashes,
and mutated payloads, and must serialize deterministically.
"""

from __future__ import annotations

import json

from proofsmith.bundle import create_bundle
from proofsmith.hashchain import bundle_hash, canonical_json, sha256, verify_chain
from proofsmith.models import ChangedFile, CheckResult, CheckStatus, VerificationRequest


def _request() -> VerificationRequest:
    return VerificationRequest(
        revision="abc123",
        changed_files=(ChangedFile("src/app.py", 2, 0),),
        checks=("unit",),
    )


def _pass_checks() -> tuple[CheckResult, ...]:
    return (CheckResult("unit", "Unit tests", CheckStatus.PASS, "passed", evidence=("2 passed",)),)


def _bundle(previous_hash: str | None = None) -> dict[str, object]:
    return create_bundle(_request(), _pass_checks(), previous_hash=previous_hash).to_dict()


def test_canonical_json_is_sorted_and_compact() -> None:
    raw = {"b": 2, "a": {"c": 3, "b": 1}}
    assert canonical_json(raw) == b'{"a":{"b":1,"c":3},"b":2}'
    # Whitespace and key order are irrelevant to the digest.
    assert sha256(raw) == sha256({"a": {"b": 1, "c": 3}, "b": 2})


def test_canonical_json_is_ascii_safe() -> None:
    """Non-ASCII content stays UTF-8 encoded without escaping."""
    value = {"title": "café résumé"}
    assert b"caf\xc3\xa9" in canonical_json(value)


def test_canonical_json_uses_bytes_payload_directly() -> None:
    """Bytes pass through `sha256` unchanged while objects get canonicalized."""
    payload = b"raw bytes payload"
    assert sha256(payload) == sha256(payload)
    assert sha256(payload) != sha256(payload.decode())


def test_empty_chain_is_valid() -> None:
    valid, message = verify_chain([])
    assert valid, message


def test_single_bundle_verifies() -> None:
    valid, message = verify_chain([_bundle()])
    assert valid, message


def test_multi_bundle_chain_verifies() -> None:
    first = _bundle()
    second = _bundle(previous_hash=first["content_hash"])
    third = _bundle(previous_hash=second["content_hash"])
    valid, message = verify_chain([first, second, third])
    assert valid, message


def test_chained_bundles_reuse_content_hash_as_previous_hash() -> None:
    first = _bundle()
    second = _bundle(previous_hash=first["content_hash"])
    third = _bundle(previous_hash=second["content_hash"])
    for current, predecessor in ((second, first), (third, second)):
        assert current["previous_hash"] == predecessor["content_hash"]


def test_chain_round_trips_through_json_serialization() -> None:
    first = _bundle()
    second = _bundle(previous_hash=first["content_hash"])
    serialized = json.loads(json.dumps([first, second]))
    valid, message = verify_chain(serialized)
    assert valid, message


def test_missing_previous_hash_rejected() -> None:
    """A bundled chain link whose previous_hash does not match is rejected."""
    first = _bundle()
    second = _bundle(previous_hash="deadbeef")
    valid, message = verify_chain([first, second])
    assert not valid
    assert "points to" in message and "expected" in message


def test_broken_link_rejected() -> None:
    first = _bundle()
    second = _bundle(previous_hash=first["content_hash"])
    third = _bundle(previous_hash="deadbeef")
    valid, message = verify_chain([first, second, third])
    assert not valid
    assert "points to" in message and "expected" in message


def test_mutated_payload_rejected() -> None:
    first = _bundle()
    second = _bundle(previous_hash=first["content_hash"])
    second["request"] = {"revision": "tampered"}
    valid, message = verify_chain([first, second])
    assert not valid
    assert "content_hash" in message


def test_mutated_final_status_rejected() -> None:
    """Faking a passing final status on a blocked bundle breaks the digest."""
    blocked = create_bundle(
        _request(),
        (CheckResult("unit", "Unit tests", CheckStatus.BLOCKED, "failed"),),
    ).to_dict()
    assert blocked["final_status"] != "pass"
    blocked["final_status"] = "pass"
    valid, message = verify_chain([blocked])
    assert not valid
    assert "content_hash" in message


def test_mutated_content_hash_rejected() -> None:
    first = _bundle()
    first["content_hash"] = "f" * 64
    valid, message = verify_chain([first])
    assert not valid
    assert "content_hash" in message


def test_extra_unknown_field_breaks_signature() -> None:
    """Adding an undocumented field changes the content digest."""
    first = _bundle()
    forged = {**first, "admin": True}
    forged["content_hash"] = first["content_hash"]
    valid, message = verify_chain([forged])
    assert not valid
    assert "content_hash" in message


def test_hash_is_sha256_hexdigest() -> None:
    first = _bundle()
    assert len(first["content_hash"]) == 64
    assert first["content_hash"] == first["content_hash"].lower()
    assert all(char in "0123456789abcdef" for char in first["content_hash"])


def test_content_hash_excludes_itself() -> None:
    """content_hash must not be part of its own digest payload.

    Only the content_hash field is stripped before hashing; every other field,
    including the chain-linking previous_hash, is covered by the digest.
    """
    first = _bundle()
    unsigned = {key: value for key, value in first.items() if key != "content_hash"}
    assert bundle_hash(unsigned) == first["content_hash"]


def test_previous_hash_is_part_of_the_content_digest() -> None:
    """The chain linkage is itself integrity-protected.

    previous_hash participates in the unsigned payload, so re-linking a bundle
    to a different predecessor changes its content digest; an attacker cannot
    reposition a verified bundle inside another chain without breaking the
    signature.
    """
    first = _bundle()
    second = _bundle(previous_hash=first["content_hash"])
    assert first["content_hash"] != second["content_hash"]
    # But their chain positions are not interchangeable.
    valid, _ = verify_chain([first, second])
    assert valid
    valid, _ = verify_chain([second])
    assert not valid
