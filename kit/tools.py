"""Profile tools: decide what to check or install, then do it (uv tool, then pip --user)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import preflight
from .model import FAIL, PASS, SKIPPED, UNVERIFIED, ItemResult
from .preflight import EnvReport
from .profiles import Profile

PRESENT = "present"
INSTALL = "install"
MISSING = "missing"
OFFLINE = "offline"
ADVICE = "advice"
REPORT = "report"
ATTEMPTS = 2  # first try plus one retry per command

Runner = Callable[[list[str]], tuple[int, str]]


@dataclass
class ToolAction:
    name: str
    kind: str
    status: str
    command: str = ""
    commands: list[list[str]] = field(default_factory=list)
    detail: str = ""


def run_command(cmd: list[str], timeout: float = 600.0, cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout + proc.stderr


def show(cmd: list[str]) -> str:
    return " ".join([Path(cmd[0]).stem, *cmd[1:]])


def install_commands(spec: dict, env: EnvReport) -> list[list[str]]:
    pinned = f"{spec['package']}=={spec['version']}"
    commands = []
    uv = env.tools.get("uv")
    if uv is not None and uv.ok and uv.path:
        commands.append([uv.path, "tool", "install", pinned])
    commands.append([sys.executable, "-m", "pip", "install", "--user", pinned])
    return commands


def _importable(package: str) -> bool:
    try:
        return importlib.util.find_spec(package) is not None
    except (ImportError, ValueError):
        return False


def plan_tools(
    profile: Profile, env: EnvReport, offline: bool, verify_only: bool
) -> list[ToolAction]:
    actions = []
    for spec in profile.tools:
        kind = spec["kind"]
        if kind == "python-lib":
            if _importable(spec["package"]):
                actions.append(ToolAction(spec["name"], kind, PRESENT, detail="importable"))
            else:
                advice = (
                    "not installed by the kit; if you need it: "
                    f"python -m pip install --user {spec['package']}"
                )
                actions.append(ToolAction(spec["name"], kind, ADVICE, detail=advice))
        elif kind == "python-tool":
            info = preflight.probe_tool(spec["command"])
            if info.ok:
                actions.append(
                    ToolAction(spec["name"], kind, PRESENT, spec["command"], detail=info.version)
                )
                continue
            if verify_only:
                status = MISSING
            elif offline:
                status = OFFLINE
            elif profile.report_only:
                status = REPORT
            else:
                status = INSTALL
            actions.append(
                ToolAction(spec["name"], kind, status, spec["command"], install_commands(spec, env))
            )
    return actions


def run_tools(actions: list[ToolAction], runner: Runner | None = None) -> list[ItemResult]:
    runner = runner or run_command
    return [_run_one(action, runner) for action in actions]


def _run_one(action: ToolAction, runner: Runner) -> ItemResult:
    label = f"tool:{action.name}"
    if action.status == PRESENT:
        return ItemResult(label, False, True, True, PASS, action.detail)
    if action.status == ADVICE:
        return ItemResult(label, False, False, False, SKIPPED, action.detail)
    alternatives = " or ".join(show(c) for c in action.commands)
    if action.status == MISSING:
        detail = f"not installed; run without --verify-only to install ({alternatives})"
        return ItemResult(label, False, False, False, FAIL, detail)
    if action.status == OFFLINE:
        detail = f"offline; install later with: {alternatives}"
        return ItemResult(label, False, False, False, SKIPPED, detail)
    if action.status == REPORT:
        detail = f"report only; would run: {alternatives}"
        return ItemResult(label, False, False, False, SKIPPED, detail)
    last = ""
    for cmd in action.commands:
        for _ in range(ATTEMPTS):
            code, output = runner(cmd)
            if code == 0:
                return _after_install(action, label, cmd)
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            last = lines[-1] if lines else f"exit {code}"
    return ItemResult(label, False, False, False, FAIL, f"install failed: {last}")


def _after_install(action: ToolAction, label: str, cmd: list[str]) -> ItemResult:
    if preflight.probe_tool(action.command).ok:
        return ItemResult(label, False, True, True, PASS, f"installed with {show(cmd)}")
    detail = (
        f"installed with {show(cmd)} but `{action.command}` is not on PATH; "
        "open a new shell or add the scripts folder to PATH"
    )
    return ItemResult(label, False, True, False, UNVERIFIED, detail)


def network_used(actions: list[ToolAction]) -> list[str]:
    return [show(a.commands[0]) for a in actions if a.status == INSTALL]


def format_tool_plan(actions: list[ToolAction]) -> str:
    lines = []
    for action in actions:
        if action.status == INSTALL:
            chain = " -> ".join(show(c) for c in action.commands)
            suffix = f"  ({chain}) [network]"
        elif action.commands:
            suffix = f"  ({' or '.join(show(c) for c in action.commands)})"
        else:
            suffix = f"  ({action.detail})" if action.detail else ""
        lines.append(f"  {action.status.upper():<9} tool:{action.name}{suffix}")
    return "\n".join(lines)
