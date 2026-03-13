from __future__ import annotations

import argparse
import json
import sys

from .core import build_check_result, docs_skill, fix_skill, inspect_skill
from .models import CommandResult, to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python-skill-doctor", description="Inspect and repair Python-based skills"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Inspect a skill directory")
    check.add_argument("skill_path")
    check.add_argument("--json", action="store_true", dest="json_output")
    check.add_argument("--strict", action="store_true")
    check.add_argument("--deps")
    check.add_argument("--entry")

    fix = subparsers.add_parser("fix", help="Create .venv and install dependencies")
    fix.add_argument("skill_path")
    fix.add_argument("--json", action="store_true", dest="json_output")
    fix.add_argument("--deps")
    fix.add_argument("--entry")
    fix.add_argument("--dry-run", action="store_true")
    fix.add_argument("--skip-install", action="store_true")
    fix.add_argument("--skip-smoke", action="store_true")
    fix.add_argument("--uv", action="store_true")
    fix.add_argument("--pip", action="store_true")
    fix.add_argument("--recreate-venv", action="store_true")

    docs = subparsers.add_parser("docs", help="Generate or write SKILL.md guidance")
    docs.add_argument("skill_path")
    docs.add_argument("--json", action="store_true", dest="json_output")
    docs.add_argument("--deps")
    docs.add_argument("--entry")
    docs.add_argument("--write", action="store_true")
    docs.add_argument("--format", choices=["text", "patch", "full"], default="patch")

    return parser


def _print_result(payload, as_json: bool) -> None:
    if as_json:
        print(json.dumps(to_dict(payload), indent=2))
        return
    if hasattr(payload, "inspection"):
        inspection = payload.inspection
        print(f"Skill: {inspection.skill.name or '(unknown)'}")
        print(f"Path: {inspection.skill.path}")
        print(f"Result: {payload.result}")
        if inspection.dependency_file:
            print(f"Dependency file: {inspection.dependency_file.path}")
        if inspection.entry_script:
            print(f"Entry script: {inspection.entry_script.path}")
        if inspection.venv:
            print(f"Virtualenv: {'present' if inspection.venv.exists else 'missing'}")
        if inspection.issues:
            print("Issues:")
            for issue in inspection.issues:
                print(f"- [{issue.severity}] {issue.code}: {issue.message}")
        if getattr(payload, "actions", None):
            print("Actions:")
            for action in payload.actions:
                print(f"- [{action.status}] {action.code}: {action.message}")
        write_result = getattr(payload, "write_result", None)
        if write_result and getattr(write_result, "status", None) == "written":
            print(write_result.message)
        elif getattr(payload, "patch", None):
            print(payload.patch.content)
        if getattr(payload, "suggested_next_command", None):
            print(f"Suggested next step: {payload.suggested_next_command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    inspection = inspect_skill(
        args.skill_path,
        deps_override=getattr(args, "deps", None),
        entry_override=getattr(args, "entry", None),
    )

    if args.command == "check":
        result = build_check_result(inspection)
        _print_result(result, args.json_output)
        if result.result == CommandResult.FATAL:
            return 1
        if result.result == CommandResult.ISSUES_FOUND:
            return 2
        return 0

    if args.command == "fix":
        result = fix_skill(
            inspection,
            dry_run=args.dry_run,
            skip_install=args.skip_install,
            skip_smoke=args.skip_smoke,
            force_uv=args.uv,
            force_pip=args.pip,
            recreate_venv=args.recreate_venv,
        )
        _print_result(result, args.json_output)
        if result.result == CommandResult.FATAL:
            return 1
        if result.result in {CommandResult.PARTIAL_SUCCESS, CommandResult.DRY_RUN}:
            return 2 if result.result == CommandResult.PARTIAL_SUCCESS else 0
        return 0

    result = docs_skill(inspection, fmt=args.format, write=args.write)
    _print_result(result, args.json_output)
    if result.result == CommandResult.FATAL:
        return 1
    if result.result == CommandResult.ISSUES_FOUND:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
