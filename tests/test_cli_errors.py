"""Defensive CLI error-contract coverage.

The baseline suite verified one invalid-JSON failure path. These tests lock in
the full error contract: any parsing or I/O failure returns exit code `2` with
an actionable `proofsmith:` stderr prefix, and a missing command is rejected.
"""

from __future__ import annotations

import json
from pathlib import Path

from proofsmith.cli import main


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload))


def _exit_code(argv: list[str]) -> int:
    try:
        return main(argv)
    except SystemExit as error:
        return int(error.code)


def test_missing_command_rejected_with_exit_two(capsys) -> None:
    assert _exit_code([]) == 2
    captured = capsys.readouterr()
    assert "required" in captured.err


def test_unknown_command_rejected_with_exit_two(capsys) -> None:
    assert _exit_code(["unknown"]) == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err or "unknown" in captured.err


def test_plan_invalid_json_returns_exit_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "broken.json"
    source.write_text("not-json")
    assert main(["plan", str(source)]) == 2
    assert "proofsmith:" in capsys.readouterr().err


def test_bundle_invalid_json_returns_exit_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "broken.json"
    source.write_text("{")
    assert main(["bundle", str(source)]) == 2
    assert "proofsmith:" in capsys.readouterr().err


def test_plan_missing_input_file_returns_exit_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "missing.json"
    assert main(["plan", str(source)]) == 2
    assert "proofsmith:" in capsys.readouterr().err


def test_bundle_malformed_payload_returns_exit_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "malformed.json"
    _write_json(source, {"revision": "abc", "changed_files": "not-a-list"})
    assert main(["bundle", str(source)]) == 2
    assert "proofsmith:" in capsys.readouterr().err


def test_bundle_invalid_check_status_returns_exit_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "bad_status.json"
    _write_json(
        source,
        {
            "revision": "abc",
            "changed_files": [{"path": "src/app.py"}],
            "checks": [{"check_id": "unit", "status": "unknown"}],
        },
    )
    assert main(["bundle", str(source)]) == 2
    assert "proofsmith:" in capsys.readouterr().err


def test_verify_missing_bundle_returns_exit_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "missing.json"
    assert main(["verify", str(source)]) == 2
    assert "proofsmith:" in capsys.readouterr().err
