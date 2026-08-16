"""Command-line interface for ProofSmith."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bundle import create_bundle, read_bundle, write_bundle
from .hashchain import verify_chain
from .impact import plan_for
from .models import ChangedFile, CheckResult, CheckStatus, VerificationRequest


def _files_from_payload(payload: dict[str, object]) -> tuple[ChangedFile, ...]:
    raw_files = payload.get("changed_files", [])
    if not isinstance(raw_files, list):
        raise ValueError("changed_files must be a list")
    return tuple(
        ChangedFile(
            path=str(item["path"]),
            additions=int(item.get("additions", 0)),
            deletions=int(item.get("deletions", 0)),
            status=str(item.get("status", "modified")),
        )
        for item in raw_files
        if isinstance(item, dict) and "path" in item
    )


def cmd_plan(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.input).read_text())
    plan = plan_for(_files_from_payload(payload))
    print(json.dumps({"checks": plan.checks, "reasons": plan.reasons}, indent=2))
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.input).read_text())
    files = _files_from_payload(payload)
    checks = tuple(
        CheckResult(
            check_id=str(item["check_id"]),
            title=str(item.get("title", item["check_id"])),
            status=CheckStatus(str(item.get("status", "pass"))),
            summary=str(item.get("summary", "")),
            duration_ms=int(item.get("duration_ms", 0)),
            evidence=tuple(str(value) for value in item.get("evidence", [])),
        )
        for item in payload.get("checks", [])
    )
    request = VerificationRequest(
        revision=str(payload.get("revision", "working-tree")),
        changed_files=files,
        checks=tuple(check.check_id for check in checks),
        policy_name=str(payload.get("policy_name", "default")),
        source=str(payload.get("source", "local")),
    )
    bundle = create_bundle(request, checks)
    path = write_bundle(bundle, Path(args.output))
    print(json.dumps({"bundle": str(path), "status": bundle.final_status}, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    bundles = [read_bundle(Path(item)) for item in args.bundles]
    valid, message = verify_chain(bundles)
    print(message)
    return 0 if valid else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proofsmith", description="Turn code changes into replayable evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="derive deterministic checks from changed files")
    plan.add_argument("input", type=Path)
    plan.set_defaults(func=cmd_plan)
    bundle = subparsers.add_parser(
        "bundle", help="create an evidence bundle from verification input"
    )
    bundle.add_argument("input", type=Path)
    bundle.add_argument("--output", type=Path, default=Path(".proofsmith"))
    bundle.set_defaults(func=cmd_bundle)
    verify = subparsers.add_parser("verify", help="verify one or more bundles as a hash chain")
    verify.add_argument("bundles", nargs="+", type=Path)
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"proofsmith: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
