"""Command-line parsing. Errors raise UsageError/TargetError instead of exiting."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .model import TargetError, UsageError

EPILOG = """exit codes:
  0   READY (or dry-run completed)
  1   PARTIAL - required items OK, optional items failed or unsupported
  2   BLOCKED - a required item failed or needs your decision
  64  invalid arguments
  65  target workspace missing or not a directory
"""


@dataclass(frozen=True)
class Options:
    profile: str
    target: Path
    dry_run: bool
    offline: bool
    verify_only: bool
    no_mcp: bool
    verbose: bool


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def build_parser(profiles: list[str]) -> argparse.ArgumentParser:
    parser = _Parser(
        prog="bootstrap",
        description="Install the hackathon agent kit (AGENTS.md, skills, optional tools) "
        "into a workspace.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile", default="core", choices=profiles, help="profile to install (default: core)"
    )
    parser.add_argument(
        "--target", default=None, help="workspace directory (default: current directory)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print planned changes; write nothing"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="never use the network; only use tools already present",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="check the current state; install and register nothing",
    )
    parser.add_argument("--no-mcp", action="store_true", help="skip MCP servers")
    parser.add_argument("--verbose", action="store_true", help="print per-file details")
    return parser


def parse_args(argv: list[str], cwd: Path, profiles: list[str]) -> Options:
    ns = build_parser(profiles).parse_args(argv)
    if ns.dry_run and ns.verify_only:
        raise UsageError("--dry-run and --verify-only cannot be combined")
    target = Path(ns.target) if ns.target else cwd
    if not target.is_absolute():
        target = cwd / target
    target = target.resolve()
    if not target.is_dir():
        raise TargetError(f"target is not an existing directory: {target}")
    return Options(
        ns.profile, target, ns.dry_run, ns.offline, ns.verify_only, ns.no_mcp, ns.verbose
    )
