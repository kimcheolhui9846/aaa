"""Orchestration: preflight -> plan -> apply -> verify -> report."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from . import audit, mcpconfig
from .cli import Options, parse_args
from .fsops import PathEscapeError, State, timestamp
from .logs import write_log
from .model import EXIT_BLOCKED, EXIT_READY, EXIT_TARGET, EXIT_USAGE, TargetError, UsageError
from .plan import FileChange, format_plan, plan_changes
from .preflight import EnvReport, run_preflight
from .profiles import available_profiles, load_profile
from .register import apply_changes
from .report import next_actions, overall_status, render
from .verify import verify_target

KIT_ROOT = Path(__file__).resolve().parent.parent
SELF_TARGET_MSG = (
    "target is the kit folder itself; run from your workspace or pass --target <workspace>"
)


def run(
    argv: list[str],
    cwd: Path | None = None,
    kit_root: Path = KIT_ROOT,
    out: TextIO | None = None,
) -> int:
    out = out or sys.stdout
    cwd = cwd or Path.cwd()
    try:
        opts = parse_args(argv, cwd, available_profiles(kit_root))
        profile = load_profile(kit_root, opts.profile)
        mcpconfig.select_servers(kit_root, profile.mcp)
        if opts.target == kit_root.resolve():
            raise TargetError(SELF_TARGET_MSG)
    except UsageError as exc:
        print(f"error: {exc}\nRun with --help for usage.", file=sys.stderr)
        return EXIT_USAGE
    except TargetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TARGET

    env = run_preflight(opts.target)
    state = State.load(opts.target)
    include_mcp = bool(profile.mcp) and not opts.no_mcp
    changes = plan_changes(opts.target, kit_root, profile, state, include_mcp)

    if opts.dry_run:
        out.write(_dry_run_text(opts, env, changes))
        return EXIT_READY

    stamp = timestamp()
    lines = []
    if not opts.verify_only and env.target_writable:
        try:
            apply_changes(opts.target, changes, state, stamp, opts.profile)
        except (OSError, PathEscapeError) as exc:
            lines.append(f"error: write failed: {exc}")

    items = verify_target(
        opts.target,
        kit_root,
        profile,
        changes,
        check_writable=not opts.verify_only,
        writable=env.target_writable,
        include_mcp=include_mcp,
    )
    items.append(audit.audit_target(opts.target, kit_root))
    status, code = overall_status(items)
    lines.append(render(env, opts, items, status, next_actions(items, opts.target, status)))
    text = "\n".join(lines)
    out.write(text)
    if env.target_writable:
        try:
            write_log(opts.target, text, stamp)
        except (OSError, PathEscapeError):
            pass
    return code


def main(argv: list[str]) -> int:
    """Entry-point wrapper: any unexpected error is BLOCKED, never a bare traceback."""
    try:
        return run(argv)
    except Exception as exc:
        print("Status:       BLOCKED", file=sys.stderr)
        print(f"error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_BLOCKED


def _dry_run_text(opts: Options, env: EnvReport, changes: list[FileChange]) -> str:
    return "\n".join(
        [
            f"Environment:  {env.os} {env.arch}, shell={env.shell}, python {env.python}",
            f"Target:       {opts.target}",
            f"Profile:      {opts.profile}",
            "Network:      none (this profile installs no tools)",
            "Planned changes:",
            format_plan(changes, opts.verbose),
            "DRY RUN: nothing was written.",
            "",
        ]
    )
