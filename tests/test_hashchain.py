"""Tamper-evidence coverage for canonical hashing and hash chains.

The baseline suite verified only the happy path. Because tamper-evident
chaining is the core security promise of an evidence bundle, these tests
prove the chain rejects a missing link, a broken link, and a mutated
content payload, and that canonical serialization is order-independent.
"""

from __future__ import annotations

from proofsmith.hashchain import bundle_hash, canonical_json, sha256, verify_chain


def make_bundle(payload: str = "evidence-1", previous_hash: str | None = None) -> dict:
    bundle = {
        "schema_version": "proofsmith/v1",
        "bundle_id": "b-1",
        "payload": payload,
        "previous_hash": previous_hash,
    }
    return {**bundle, "content_hash": bundle_hash(bundle)}


def test_canonical_json_is_deterministic_and_sorted() -> None:
    first = canonical_json({"b": 2, "a": 1})
    second = canonical_json({"a": 1, "b": 2})
    assert first == second
    assert b'"a":1,"b":2' in first


def test_single_bundle_with_no_previous_hash_verifies() -> None:
    bundle = make_bundle(previous_hash=None)
    valid, message = verify_chain([bundle])
    assert valid, message
    assert message == "chain verified"


def test_valid_chain_of_multiple_bundles_verifies() -> None:
    first = make_bundle("evidence-1", previous_hash=None)
    second = make_bundle("evidence-2", previous_hash=first["content_hash"])
    valid, message = verify_chain([first, second])
    assert valid, message
    assert message == "chain verified"


def test_chain_rejects_broken_previous_hash_link() -> None:
    first = make_bundle(previous_hash=None)
    second = make_bundle("evidence-2", previous_hash="deadbeef" * 4)
    valid, message = verify_chain([first, second])
    assert not valid
    assert "expected" in message


def test_chain_rejects_first_bundle_pointing_to_nonexistent_previous() -> None:
    bundle = make_bundle(previous_hash="missing-previous")
    valid, message = verify_chain([bundle])
    assert not valid
    assert message.startswith("bundle 0 points to")


def test_chain_rejects_tampered_content_payload() -> None:
    bundle = make_bundle("original", previous_hash=None)
    tampered = {**bundle, "payload": "tampered", "content_hash": bundle["content_hash"]}
    valid, message = verify_chain([tampered])
    assert not valid
    assert message == "bundle 0 has an invalid content_hash"


def test_chain_rejects_direct_content_hash_mutation() -> None:
    bundle = make_bundle(previous_hash=None)
    tampered = {**bundle, "content_hash": sha256("forged")}
    valid, message = verify_chain([tampered])
    assert not valid
    assert message == "bundle 0 has an invalid content_hash"


def test_empty_chain_verifies() -> None:
    valid, message = verify_chain([])
    assert valid, message
