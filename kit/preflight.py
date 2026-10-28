"""Environment probing: OS, shell, interpreter, tool versions, target permissions."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOOLS = ("git", "uv", "node", "npx", "codex")


@dataclass
class ToolInfo:
    name: str
    path: str | None = None
    version: str | None = None

    @property
    def ok(self) -> bool:
        return self.version is not None


@dataclass
class EnvReport:
    os: str
    arch: str
    shell: str
    python: str
    target_writable: bool
    tools: dict[str, ToolInfo] = field(default_factory=dict)


def probe_tool(name: str, timeout: float = 15.0) -> ToolInfo:
    """Find a tool on PATH and read the first line of `<tool> --version`."""
    path = shutil.which(name)
    if path is None:
        return ToolInfo(name)
    try:
        proc = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ToolInfo(name, path)
    if proc.returncode != 0:
        return ToolInfo(name, path)
    lines = [line.strip() for line in (proc.stdout + proc.stderr).splitlines() if line.strip()]
    return ToolInfo(name, path, lines[0] if lines else "unknown")


def _detect_shell() -> str:
    if os.environ.get("KIT_SHELL"):
        return os.environ["KIT_SHELL"]
    if os.name == "nt":
        return "windows"
    return os.path.basename(os.environ.get("SHELL", "sh"))


def run_preflight(target: Path) -> EnvReport:
    tools = {name: probe_tool(name) for name in TOOLS}
    tools["python"] = ToolInfo("python", sys.executable, platform.python_version())
    return EnvReport(
        os=f"{platform.system()} {platform.release()}",
        arch=platform.machine(),
        shell=_detect_shell(),
        python=platform.python_version(),
        target_writable=os.access(target, os.W_OK),
        tools=tools,
    )
