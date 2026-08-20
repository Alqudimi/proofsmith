from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofsmith.bundle import create_bundle, write_bundle
from proofsmith.git_adapter import GitDiffError, parse_numstat
from proofsmith.hashchain import verify_chain
from proofsmith.models import (
    ChangedFile,
    CheckResult,
    CheckStatus,
    EvidenceBundle,
    VerificationRequest,
)
from proofsmith.policy import Policy


@pytest.fixture()
def request_with_files() -> VerificationRequest:
    return VerificationRequest(
        revision="abc123",
        changed_files=(ChangedFile("src/app.py", 2, 1),),
        checks=("unit",),
    )


def _check(status: CheckStatus, evidence: tuple[str, ...] = ("ok",)) -> CheckResult:
    return CheckResult("unit", "Unit tests", status, "summary", evidence=evidence)


class TestPolicyGates:
    def test_policy_blocks_surfaces_exceeding_max_changed_files(self) -> None:
        files = tuple(ChangedFile(f"file-{i}.py", 1, 0) for i in range(251))
        status, reason = Policy().evaluate(files, ())
        assert status is CheckStatus.BLOCKED
        assert "251" in reason and "250" in reason

    def test_policy_requires_review_for_large_churn(self) -> None:
        files = (ChangedFile("src/app.py", 3000, 2001),)
        status, reason = Policy().evaluate(files, ())
        assert status is CheckStatus.REVIEW
        assert "5001" in reason and "5000" in reason

    def test_policy_blocks_any_non_security_blocked_check(self) -> None:
        checks = (_check(CheckStatus.BLOCKED), _check(CheckStatus.PASS))
        status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
        assert status is CheckStatus.BLOCKED
        assert "required checks failed" in reason

    def test_policy_requires_review_for_blocked_security_check_flag_off(self) -> None:
        checks = (
            CheckResult("secret-scan", "Secret scan", CheckStatus.BLOCKED, "found"),
            _check(CheckStatus.PASS),
        )
        status, reason = Policy(block_on_security_failure=False).evaluate(
            (ChangedFile("src/app.py", 1, 0),), checks
        )
        assert status is CheckStatus.BLOCKED
        assert "security gate failed" not in reason

    def test_policy_requires_review_for_human_review_check(self) -> None:
        checks = (_check(CheckStatus.REVIEW), _check(CheckStatus.PASS))
        status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
        assert status is CheckStatus.REVIEW
        assert "human review" in reason

    def test_policy_downgrades_pass_without_evidence(self) -> None:
        checks = (CheckResult("unit", "Unit tests", CheckStatus.PASS, "passed"),)
        status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
        assert status is CheckStatus.REVIEW
        assert "evidence" in reason

    def test_policy_allows_pass_with_evidence(self) -> None:
        checks = (_check(CheckStatus.PASS),)
        status, reason = Policy().evaluate((ChangedFile("src/app.py", 1, 0),), checks)
        assert status is CheckStatus.PASS
        assert "all policy gates" in reason


class TestEvidenceBundleStatusResolution:
    def test_bundle_now_resolves_blocked_over_everything(self) -> None:
        bundle = EvidenceBundle.now(
            bundle_id="b1",
            request=VerificationRequest("r", (), ("unit", "lint")),
            checks=(_check(CheckStatus.REVIEW), _check(CheckStatus.BLOCKED)),
            content_hash="x",
        )
        assert bundle.final_status is CheckStatus.BLOCKED

    def test_bundle_now_resolves_review_when_present(self) -> None:
        bundle = EvidenceBundle.now(
            bundle_id="b1",
            request=VerificationRequest("r", (), ("unit",)),
            checks=(_check(CheckStatus.REVIEW),),
            content_hash="x",
        )
        assert bundle.final_status is CheckStatus.REVIEW

    def test_bundle_now_resolves_all_skipped(self) -> None:
        bundle = EvidenceBundle.now(
            bundle_id="b1",
            request=VerificationRequest("r", (), ("unit",)),
            checks=(_check(CheckStatus.SKIPPED),),
            content_hash="x",
        )
        assert bundle.final_status is CheckStatus.SKIPPED

    def test_bundle_now_pass_with_mixed_pass_and_skipped(self) -> None:
        bundle = EvidenceBundle.now(
            bundle_id="b1",
            request=VerificationRequest("r", (), ("unit", "lint")),
            checks=(_check(CheckStatus.PASS), _check(CheckStatus.SKIPPED)),
            content_hash="x",
        )
        assert bundle.final_status is CheckStatus.PASS


class TestHashChainTamperEvidence:
    def test_verify_chain_detects_broken_previous_hash(self) -> None:
        from proofsmith.hashchain import bundle_hash

        first = {"previous_hash": None, "revision": "a"}
        first["content_hash"] = bundle_hash(first)
        second = {"previous_hash": "tampered", "revision": "b"}
        second["content_hash"] = bundle_hash(second)
        valid, message = verify_chain([first, second])
        assert not valid
        assert "tampered" in message

    def test_verify_chain_detects_invalid_content_hash(self) -> None:
        from proofsmith.hashchain import bundle_hash

        bundle = {"previous_hash": None, "revision": "abc", "checks": []}
        bundle["content_hash"] = "not-" + bundle_hash(bundle)
        valid, message = verify_chain([bundle])
        assert not valid
        assert "invalid content_hash" in message

    def test_verify_chain_validates_multi_bundle_chain(self) -> None:
        from proofsmith.hashchain import bundle_hash

        first = {"previous_hash": None, "revision": "a"}
        first["content_hash"] = bundle_hash(first)
        second = {"previous_hash": first["content_hash"], "revision": "b"}
        second["content_hash"] = bundle_hash(second)
        valid, message = verify_chain([first, second])
        assert valid, message


class TestGitAdapterEdgeCases:
    def test_parse_numstat_rejects_nul_delimited_and_empty_paths(self) -> None:
        with pytest.raises(GitDiffError, match="NUL"):
            parse_numstat("1\t0\tfile\x00next.py\n")
        with pytest.raises(GitDiffError, match="NUL"):
            parse_numstat("1\t0\t\n")

    def test_parse_numstat_ignores_blank_lines(self) -> None:
        files = parse_numstat("\n4\t1\tsrc/app.py\n  \n2\t0\tREADME.md\n")
        assert len(files) == 2

    def test_parse_numstat_rejects_non_numeric_counts(self) -> None:
        with pytest.raises(GitDiffError, match="invalid line counts"):
            parse_numstat("1.5\t0\tsrc/app.py\n")


class TestCliErrorPaths:
    def test_changed_files_must_be_a_list(self, tmp_path: Path) -> None:
        from proofsmith.cli import main

        source = tmp_path / "input.json"
        source.write_text(json.dumps({"revision": "r", "changed_files": "not-a-list"}))
        assert main(["plan", str(source)]) == 2

    def test_changed_files_accepts_partial_missing_path_items(self, tmp_path: Path) -> None:
        from proofsmith.cli import main

        source = tmp_path / "input.json"
        source.write_text(
            json.dumps(
                {
                    "revision": "r",
                    "changed_files": [{"path": "src/app.py"}, {"no_path": 1}],
                }
            )
        )
        assert main(["plan", str(source)]) == 0


class TestIntegrationBundles:
    def test_bundle_with_blocked_check_carries_blocked_status(self, tmp_path: Path) -> None:
        request = VerificationRequest(
            revision="abc123",
            changed_files=(ChangedFile("src/app.py", 1, 0),),
            checks=("unit",),
        )
        checks = (CheckResult("unit", "Unit tests", CheckStatus.BLOCKED, "failed"),)
        bundle = create_bundle(request, checks)
        assert bundle.final_status is CheckStatus.BLOCKED

        path = tmp_path / "bundles"
        written = write_bundle(bundle, path)
        stored = json.loads(written.read_text())
        assert stored["final_status"] == "blocked"
