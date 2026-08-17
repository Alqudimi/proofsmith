from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofsmith.cli import main
from proofsmith.git_adapter import GitDiffError, parse_numstat


def test_parse_numstat_handles_text_and_binary_files() -> None:
    files = parse_numstat("12\t3\tsrc/app.py\n-\t-\tassets/logo.bin\n")
    assert files[0].path == "src/app.py"
    assert files[0].churn == 15
    assert files[1].additions == 0
    assert files[1].deletions == 0


def test_parse_numstat_rejects_malformed_and_unsafe_input() -> None:
    with pytest.raises(GitDiffError, match="expected 3"):
        parse_numstat("1\tbad")
    with pytest.raises(GitDiffError, match="unsafe"):
        parse_numstat("1\t0\t../secrets.txt")
    with pytest.raises(GitDiffError, match="negative"):
        parse_numstat("-1\t0\tsrc/app.py")


def test_scan_command_accepts_a_diff_file(capsys, tmp_path: Path) -> None:
    diff = tmp_path / "numstat.txt"
    diff.write_text("4\t1\tsrc/policy.py\n2\t0\t.github/workflows/ci.yml\n")
    assert main(["scan", str(diff)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_files"][0]["path"] == "src/policy.py"
    assert "unit" in payload["checks"]
    assert "workflow-lint" in payload["checks"]
