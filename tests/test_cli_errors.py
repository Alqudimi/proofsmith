"""CLI error-path coverage for defensive argument handling.

The baseline suite exercised only the happy paths of ``proofsmith plan`` and
``proofsmith bundle``. These tests pin down the user-facing error contract
so that invalid inputs fail with a stable exit code (2) and a prefixed
message on stderr instead of crashing with a traceback.
"""

from __future__ import annotations

from proofsmith.cli import main


def test_plan_with_malformed_json_fails_with_exit_two(capsys) -> None:
    path = "tests/__init__.py" if False else "/dev/null"
    exit_code = main(["plan", path])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err.startswith("proofsmith:")


def test_bundle_with_malformed_json_fails_with_exit_two(tmp_path, capsys) -> None:
    bad_input = tmp_path / "input.json"
    bad_input.write_text("not-json")
    exit_code = main(["bundle", str(bad_input)])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err.startswith("proofsmith:")


def test_missing_command_fails_with_exit_two() -> None:
    import pytest

    with pytest.raises(SystemExit) as error:
        main([])
    assert int(error.value.code) == 2
