from __future__ import annotations

import json
from pathlib import Path

from proofsmith.cli import main


def _input(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "revision": "test-rev",
                "changed_files": [{"path": "src/app.py", "additions": 1, "deletions": 0}],
                "checks": [
                    {
                        "check_id": "unit",
                        "title": "Unit tests",
                        "status": "pass",
                        "summary": "one passed",
                        "evidence": ["pytest:1 passed"],
                    }
                ],
            }
        )
    )


def test_plan_command(capsys, tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    _input(source)
    assert main(["plan", str(source)]) == 0
    assert '"unit"' in capsys.readouterr().out


def test_bundle_and_verify_commands(capsys, tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    output = tmp_path / "bundles"
    _input(source)
    assert main(["bundle", str(source), "--output", str(output)]) == 0
    bundle = next(output.glob("*.json"))
    assert main(["verify", str(bundle)]) == 0
    assert "chain verified" in capsys.readouterr().out


def test_invalid_command_input_returns_actionable_error(capsys, tmp_path: Path) -> None:
    source = tmp_path / "broken.json"
    source.write_text("not-json")
    assert main(["plan", str(source)]) == 2
    assert "proofsmith:" in capsys.readouterr().err
