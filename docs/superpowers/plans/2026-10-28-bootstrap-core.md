# Bootstrap Core (Plan 1 of 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A one-command bootstrap that installs `AGENTS.md` and six Codex skills into a target workspace, safely (backups, protected block, conflict detection), idempotently, with a READY / PARTIAL / BLOCKED report, from both bash and PowerShell, with a copy-only fallback when Python is missing.

**Architecture:** Thin shell entry points (`bootstrap.sh`, `bootstrap.ps1`) detect Python 3.9+ and hand off to `run_kit.py` → `kit/` (standard library only). `kit/` runs preflight → plan (list of `FileChange`) → apply (atomic writes, backups, `.kit/state.json`) → verify (per-item results) → report. Without Python the shell copies files that are absent and reports PARTIAL/BLOCKED.

**Tech Stack:** Python 3.9+ standard library (runtime), pytest + ruff (dev, via uv), bash 3.2+, Windows PowerShell 5.1+.

**Spec:** `docs/superpowers/specs/2026-10-28-hackathon-agent-kit-design.md`. Plan 2 (python/data/web/full profiles, sequential-thinking MCP, security audit module, remaining docs) is written after this plan is done.

## Global Constraints

- Runtime code in `kit/` and `run_kit.py` imports only the Python standard library; must run on Python 3.9 (`from __future__ import annotations` in every module that has type annotations; no `match`, no `X | Y` outside annotations).
- Lint steps: if `ruff check` reports only import-order (I001) or `ruff format --check` reports formatting, run `uv run ruff check --fix . && uv run ruff format .` and re-check. Any other ruff error is a real bug to fix.
- `kit/` never imports `socket`, `urllib`, `http` (enforced by a test).
- No `git push`, no `curl … | sh`, no `Invoke-Expression`/`| iex` anywhere in code (enforced by a test).
- Never write outside the target workspace; every write path goes through `fsops.safe_path`.
- Never modify `~/.codex`, `~/.agents`, or any user-global config. Tests isolate `HOME`/`USERPROFILE`.
- Exit codes: `0` READY (or dry-run done), `1` PARTIAL, `2` BLOCKED, `64` invalid arguments, `65` target missing / not a directory.
- Required items: target writable (when writing), `AGENTS.md` kit block, skills `task-router`, `tdd-automator`, `algorithm-optimizer`, `submission-validator`. Optional: `implementation-review`, `benchmark`.
- Protected block markers: `<!-- hackathon-kit:begin -->` and `<!-- hackathon-kit:end -->`.
- `AGENTS.md` and `SKILL.md` content in English. `README.md` and `docs/` in Korean.
- Every `SKILL.md` description: one double-quoted line, starts with `Use when` or `Use only when`, contains `Do NOT use`, ≤ 400 chars; all six together ≤ 2000 chars.
- `bootstrap.ps1` is ASCII-only (Windows PowerShell 5.1 reads BOM-less files as ANSI).
- All text files checked out with LF (`.gitattributes`), so file hashes match across OSes.
- Commit author is the user alone: no `Co-Authored-By` or generated-by trailers.
- Run commands from the repo root `D:\aaa\aaa` on branch `feat/bootstrap-kit`. Run Python via `uv run`.

---

## File Map

| Path | Responsibility |
|---|---|
| `.gitattributes`, `.gitignore`, `pyproject.toml`, `LICENSE` | Repo setup; LF everywhere; dev deps; ruff/pytest config |
| `AGENTS.md` | Policy text the kit installs (body of the protected block) |
| `.agents/skills/<name>/SKILL.md` (+ `references/`, `examples/`, `agents/openai.yaml`) | The six skills |
| `profiles/core.json` | Default profile: which skills, which are required |
| `kit/model.py` | Exit codes, verdict constants, `Outcome`, `ItemResult`, errors |
| `kit/profiles.py` | Load profiles with `extends` |
| `kit/cli.py` | Parse arguments into `Options` |
| `kit/preflight.py` | Environment and tool probing |
| `kit/skills.py` | Frontmatter parsing, skill validation |
| `kit/fsops.py` | Safe paths, hashing, `.kit/state.json`, backups |
| `kit/agentsmd.py` | Protected-block merge for `AGENTS.md` |
| `kit/plan.py` | Build the list of `FileChange` |
| `kit/register.py` | Apply changes atomically with backups |
| `kit/verify.py` | Per-item verification |
| `kit/report.py` | Overall status, next actions, report text |
| `kit/logs.py` | Secret masking, local log file |
| `kit/app.py`, `kit/__main__.py`, `run_kit.py` | Orchestration and entry |
| `bootstrap.sh`, `bootstrap.ps1` | Shell entry points + shell-only fallback |
| `tests/…` | One test module per unit plus end-to-end and entry-point tests |
| `README.md`, `docs/ASSUMPTIONS.md`, `docs/TEST_REPORT.md` | Plan-1 docs |

---

### Task 1: Repository scaffolding and shared model

**Files:**
- Create: `.gitattributes`, `.gitignore`, `pyproject.toml`, `LICENSE`, `kit/__init__.py`, `kit/model.py`, `tests/conftest.py`, `tests/test_model.py`

**Interfaces:**
- Produces: `kit.model` — `EXIT_READY=0`, `EXIT_PARTIAL=1`, `EXIT_BLOCKED=2`, `EXIT_USAGE=64`, `EXIT_TARGET=65`; verdicts `PASS`, `FAIL`, `UNVERIFIED`, `SKIPPED`, `CONFLICT` (strings equal to their names); `class Outcome` with `CREATE="create"`, `UPDATE="update"`, `APPEND="append"`, `CONFLICT="conflict"`, `UNCHANGED="unchanged"`, `ALL` tuple in that order; `class UsageError(Exception)`, `class TargetError(Exception)`; `@dataclass ItemResult(name: str, required: bool, installed: bool, registered: bool, verified: str, detail: str = "")`.
- Produces: fixtures `kit_root` (repo root `Path`), `workspace` (empty tmp dir), autouse `isolated_home`.

- [ ] **Step 1: Write repo config files**

`.gitattributes`:
```
* text=auto eol=lf
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.kit/
```

`pyproject.toml`:
```toml
[project]
name = "hackathon-agent-kit"
version = "0.1.0"
description = "Bootstrap kit that installs AGENTS.md and Codex skills into a workspace"
requires-python = ">=3.9"
dependencies = []

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = ["real_preflight: run real tool probes instead of the fast fake"]

[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B"]
```

`LICENSE`: standard MIT text with `Copyright (c) 2026 kim cheol hui`.

- [ ] **Step 2: Add dev dependencies**

Run: `uv add --dev pytest ruff`
Expected: `uv.lock` created, `[dependency-groups] dev = [...]` added to `pyproject.toml`.

- [ ] **Step 3: Write the failing test**

`tests/conftest.py`:
```python
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parent.parent


def tree_digest(root: Path, exclude: tuple[str, ...] = (".kit/logs/",)) -> dict[str, str]:
    """Map every file under root (POSIX relative path) to its SHA-256."""
    digest = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith(exclude):
            digest[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


@pytest.fixture
def kit_root() -> Path:
    return KIT_ROOT


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch) -> Path:
    """Keep every test away from the real ~/.codex and ~/.agents."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


@pytest.fixture
def workspace(tmp_path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws
```

`tests/test_model.py`:
```python
from kit import model


def test_exit_codes():
    codes = [model.EXIT_READY, model.EXIT_PARTIAL, model.EXIT_BLOCKED,
             model.EXIT_USAGE, model.EXIT_TARGET]
    assert codes == [0, 1, 2, 64, 65]


def test_outcomes_are_ordered():
    assert model.Outcome.ALL == ("create", "update", "append", "conflict", "unchanged")


def test_item_result_defaults():
    item = model.ItemResult("AGENTS.md", True, True, True, model.PASS)
    assert item.detail == ""
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_model.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kit'`.

- [ ] **Step 5: Implement**

`kit/__init__.py`:
```python
"""Hackathon agent kit: installs AGENTS.md and Codex skills into a workspace."""
```

`kit/model.py`:
```python
"""Shared result types, verdicts and exit codes."""

from __future__ import annotations

from dataclasses import dataclass

EXIT_READY = 0
EXIT_PARTIAL = 1
EXIT_BLOCKED = 2
EXIT_USAGE = 64
EXIT_TARGET = 65

PASS = "PASS"
FAIL = "FAIL"
UNVERIFIED = "UNVERIFIED"
SKIPPED = "SKIPPED"
CONFLICT = "CONFLICT"


class Outcome:
    """What the planner decided to do with one file."""

    CREATE = "create"
    UPDATE = "update"
    APPEND = "append"
    CONFLICT = "conflict"
    UNCHANGED = "unchanged"
    ALL = (CREATE, UPDATE, APPEND, CONFLICT, UNCHANGED)


class UsageError(Exception):
    """Invalid command-line arguments (exit 64)."""


class TargetError(Exception):
    """Target workspace is missing or not a directory (exit 65)."""


@dataclass
class ItemResult:
    name: str
    required: bool
    installed: bool
    registered: bool
    verified: str
    detail: str = ""
```

- [ ] **Step 6: Run tests and lint**

Run: `uv run pytest -q` → Expected: 3 passed.
Run: `uv run ruff check . && uv run ruff format --check .` → Expected: no errors (run `uv run ruff format .` first if format check fails).

- [ ] **Step 7: Renormalize line endings and commit**

```bash
git add --renormalize .
git add .gitattributes .gitignore pyproject.toml uv.lock LICENSE kit tests
git commit -m "chore: scaffold kit package, dev tooling and shared model"
```

---

### Task 2: Profiles and command-line parsing

**Files:**
- Create: `profiles/core.json`, `kit/profiles.py`, `kit/cli.py`, `tests/test_profiles.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `kit.model.UsageError`, `kit.model.TargetError`.
- Produces: `kit.profiles.Profile(name: str, description: str, skills: list[str], required_skills: list[str], tools: list[dict], mcp: list[str])`; `available_profiles(kit_root: Path) -> list[str]`; `load_profile(kit_root: Path, name: str) -> Profile` (raises `UsageError`).
- Produces: `kit.cli.Options(profile: str, target: Path, dry_run: bool, offline: bool, verify_only: bool, no_mcp: bool, verbose: bool)` (frozen); `parse_args(argv: list[str], cwd: Path, profiles: list[str]) -> Options` (raises `UsageError`/`TargetError`; `--help` raises `SystemExit(0)`).

- [ ] **Step 1: Write the failing tests**

`tests/test_profiles.py`:
```python
import json

import pytest

from kit.model import UsageError
from kit.profiles import available_profiles, load_profile

ALL_SKILLS = ["task-router", "tdd-automator", "algorithm-optimizer",
              "submission-validator", "implementation-review", "benchmark"]


def _write(root, name, data):
    folder = root / "profiles"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def test_core_profile(kit_root):
    profile = load_profile(kit_root, "core")
    assert profile.skills == ALL_SKILLS
    assert profile.required_skills == ALL_SKILLS[:4]
    assert profile.tools == [] and profile.mcp == []


def test_extends_merges_lists_base_first(tmp_path):
    _write(tmp_path, "base", {"name": "base", "description": "b",
                              "skills": ["a", "b"], "tools": [{"name": "pytest"}]})
    _write(tmp_path, "child", {"name": "child", "description": "c", "extends": "base",
                               "skills": ["b", "c"], "tools": [{"name": "ruff"}]})
    profile = load_profile(tmp_path, "child")
    assert profile.skills == ["a", "b", "c"]
    assert profile.tools == [{"name": "pytest"}, {"name": "ruff"}]
    assert profile.description == "c"


def test_cycle_is_rejected(tmp_path):
    _write(tmp_path, "a", {"name": "a", "extends": "b"})
    _write(tmp_path, "b", {"name": "b", "extends": "a"})
    with pytest.raises(UsageError, match="cycle"):
        load_profile(tmp_path, "a")


def test_unknown_profile_lists_available(tmp_path):
    _write(tmp_path, "base", {"name": "base"})
    with pytest.raises(UsageError, match="available: base"):
        load_profile(tmp_path, "nope")


def test_available_profiles_sorted(tmp_path):
    _write(tmp_path, "web", {"name": "web"})
    _write(tmp_path, "core", {"name": "core"})
    assert available_profiles(tmp_path) == ["core", "web"]
```

`tests/test_cli.py`:
```python
import pytest

from kit.cli import parse_args
from kit.model import TargetError, UsageError

PROFILES = ["core"]


def test_defaults(workspace):
    opts = parse_args([], workspace, PROFILES)
    assert opts.profile == "core"
    assert opts.target == workspace.resolve()
    assert not (opts.dry_run or opts.offline or opts.verify_only or opts.no_mcp or opts.verbose)


def test_flags(workspace):
    opts = parse_args(["--dry-run", "--offline", "--no-mcp", "--verbose"], workspace, PROFILES)
    assert opts.dry_run and opts.offline and opts.no_mcp and opts.verbose


def test_relative_target_resolves_against_cwd(tmp_path, workspace):
    opts = parse_args(["--target", "ws"], tmp_path, PROFILES)
    assert opts.target == workspace.resolve()


def test_unknown_flag(workspace):
    with pytest.raises(UsageError):
        parse_args(["--bogus"], workspace, PROFILES)


def test_unknown_profile(workspace):
    with pytest.raises(UsageError):
        parse_args(["--profile", "gpu"], workspace, PROFILES)


def test_missing_target(tmp_path):
    with pytest.raises(TargetError):
        parse_args(["--target", str(tmp_path / "missing")], tmp_path, PROFILES)


def test_target_is_a_file(tmp_path):
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    with pytest.raises(TargetError):
        parse_args(["--target", "f.txt"], tmp_path, PROFILES)


def test_dry_run_and_verify_only_conflict(workspace):
    with pytest.raises(UsageError, match="cannot be combined"):
        parse_args(["--dry-run", "--verify-only"], workspace, PROFILES)


def test_help_exits_zero(workspace, capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(["--help"], workspace, PROFILES)
    assert exc.value.code == 0
    assert "exit codes" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_profiles.py tests/test_cli.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kit.profiles'`.

- [ ] **Step 3: Implement**

`profiles/core.json`:
```json
{
  "name": "core",
  "description": "AGENTS.md and the six kit skills. Installs no tools and no MCP servers.",
  "extends": null,
  "skills": [
    "task-router",
    "tdd-automator",
    "algorithm-optimizer",
    "submission-validator",
    "implementation-review",
    "benchmark"
  ],
  "required_skills": [
    "task-router",
    "tdd-automator",
    "algorithm-optimizer",
    "submission-validator"
  ],
  "tools": [],
  "mcp": []
}
```

`kit/profiles.py`:
```python
"""Profile loading. A profile may extend another; list fields merge base-first."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .model import UsageError

LIST_KEYS = ("skills", "required_skills", "tools", "mcp")


@dataclass
class Profile:
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    mcp: list[str] = field(default_factory=list)


def available_profiles(kit_root: Path) -> list[str]:
    return sorted(path.stem for path in (kit_root / "profiles").glob("*.json"))


def _read(kit_root: Path, name: str) -> dict:
    path = kit_root / "profiles" / f"{name}.json"
    if not path.is_file():
        available = ", ".join(available_profiles(kit_root))
        raise UsageError(f"unknown profile '{name}' (available: {available})")
    return json.loads(path.read_text(encoding="utf-8"))


def load_profile(kit_root: Path, name: str) -> Profile:
    chain: list[dict] = []
    seen: set[str] = set()
    current: str | None = name
    while current:
        if current in seen:
            raise UsageError(f"profile inheritance cycle at '{current}'")
        seen.add(current)
        data = _read(kit_root, current)
        chain.append(data)
        current = data.get("extends")

    merged: dict[str, list] = {key: [] for key in LIST_KEYS}
    for data in reversed(chain):
        for key in LIST_KEYS:
            for item in data.get(key, []):
                if item not in merged[key]:
                    merged[key].append(item)
    return Profile(name=name, description=chain[0].get("description", ""), **merged)
```

`kit/cli.py`:
```python
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
    parser.add_argument("--profile", default="core", choices=profiles,
                        help="profile to install (default: core)")
    parser.add_argument("--target", default=None,
                        help="workspace directory (default: current directory)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print planned changes; write nothing")
    parser.add_argument("--offline", action="store_true",
                        help="never use the network; only use tools already present")
    parser.add_argument("--verify-only", action="store_true",
                        help="check the current state; install and register nothing")
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
    return Options(ns.profile, target, ns.dry_run, ns.offline, ns.verify_only,
                   ns.no_mcp, ns.verbose)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_profiles.py tests/test_cli.py -q`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add profiles kit/profiles.py kit/cli.py tests/test_profiles.py tests/test_cli.py
git commit -m "feat: add core profile, profile inheritance and argument parsing"
```

---

### Task 3: Preflight

**Files:**
- Create: `kit/preflight.py`, `tests/test_preflight.py`
- Modify: `tests/conftest.py` (add autouse `fast_preflight`)

**Interfaces:**
- Produces: `kit.preflight.TOOLS = ("git", "uv", "node", "npx", "codex")`; `ToolInfo(name: str, path: str | None = None, version: str | None = None)` with property `ok -> bool` (`version is not None`); `EnvReport(os: str, arch: str, shell: str, python: str, target_writable: bool, tools: dict[str, ToolInfo])`; `probe_tool(name: str, timeout: float = 15.0) -> ToolInfo`; `run_preflight(target: Path) -> EnvReport` (always includes `tools["python"]` for the running interpreter).
- Produces: conftest autouse fixture `fast_preflight` that replaces `preflight.probe_tool` with a fake returning `ToolInfo(name, f"/fake/{name}", "fake 1.0")` unless the test has marker `real_preflight`.

- [ ] **Step 1: Write the failing tests**

`tests/test_preflight.py`:
```python
import os
import platform

import pytest

from kit import preflight

pytestmark = pytest.mark.real_preflight


@pytest.fixture
def fake_tools(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if os.name == "nt":
        (bin_dir / "faketool.cmd").write_text("@echo fake-tool 9.9.9\r\n", encoding="ascii")
        (bin_dir / "brokentool.cmd").write_text("@exit /b 3\r\n", encoding="ascii")
    else:
        for name, body in (("faketool", "echo fake-tool 9.9.9"), ("brokentool", "exit 3")):
            script = bin_dir / name
            script.write_text(f"#!/bin/sh\n{body}\n", encoding="ascii")
            script.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return bin_dir


def test_probe_reports_first_version_line(fake_tools):
    info = preflight.probe_tool("faketool")
    assert info.ok
    assert info.version == "fake-tool 9.9.9"


def test_probe_missing_tool():
    info = preflight.probe_tool("definitely-not-a-tool-xyz")
    assert info.path is None
    assert not info.ok


def test_probe_failing_tool(fake_tools):
    info = preflight.probe_tool("brokentool")
    assert info.path is not None
    assert not info.ok


def test_run_preflight_reports_python_and_writable(workspace, monkeypatch):
    monkeypatch.setattr(preflight, "TOOLS", ())
    env = preflight.run_preflight(workspace)
    assert env.python == platform.python_version()
    assert env.tools["python"].ok
    assert env.target_writable


def test_shell_comes_from_entry_point(workspace, monkeypatch):
    monkeypatch.setattr(preflight, "TOOLS", ())
    monkeypatch.setenv("KIT_SHELL", "bash")
    assert preflight.run_preflight(workspace).shell == "bash"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_preflight.py -q`
Expected: FAIL — `ImportError: cannot import name 'preflight'`.

- [ ] **Step 3: Implement**

`kit/preflight.py`:
```python
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
        proc = subprocess.run([path, "--version"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
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
```

Append to `tests/conftest.py` (add `from kit import preflight` and `from kit.preflight import ToolInfo` to the imports):
```python
@pytest.fixture(autouse=True)
def fast_preflight(request, monkeypatch):
    """Skip slow real tool probes unless the test is marked real_preflight."""
    if request.node.get_closest_marker("real_preflight"):
        return
    monkeypatch.setattr(preflight, "probe_tool",
                        lambda name, timeout=15.0: ToolInfo(name, f"/fake/{name}", "fake 1.0"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add kit/preflight.py tests/test_preflight.py tests/conftest.py
git commit -m "feat: add preflight environment and tool probing"
```

---

### Task 4: AGENTS.md, skill validator and the four core skills

**Files:**
- Create: `AGENTS.md`, `kit/skills.py`, `tests/test_skills.py`
- Create: `.agents/skills/task-router/SKILL.md`, `.agents/skills/task-router/examples/example.md`
- Create: `.agents/skills/tdd-automator/SKILL.md`, `.../references/languages.md`, `.../examples/example.md`
- Create: `.agents/skills/algorithm-optimizer/SKILL.md`, `.../references/languages.md`, `.../examples/example.md`
- Create: `.agents/skills/submission-validator/SKILL.md`, `.../references/languages.md`, `.../examples/example.md`

**Interfaces:**
- Produces: `kit.skills.MAX_DESCRIPTION = 400`; `parse_frontmatter(text: str) -> dict[str, str]` (raises `ValueError`); `validate_skill(skill_dir: Path) -> list[str]` (empty list means valid).
- Produces: kit `AGENTS.md` body (no markers; the kit adds them).

- [ ] **Step 1: Write the failing tests**

`tests/test_skills.py`:
```python
import pytest

from kit.skills import MAX_DESCRIPTION, parse_frontmatter, validate_skill

CORE = ["task-router", "tdd-automator", "algorithm-optimizer", "submission-validator"]
WITH_LANGUAGES = ["tdd-automator", "algorithm-optimizer", "submission-validator"]


def _skill(root, name, frontmatter):
    folder = root / name
    folder.mkdir()
    (folder / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Body\n", encoding="utf-8")
    return folder


def test_parse_frontmatter_strips_quotes():
    text = '---\nname: x\ndescription: "a: b"\n---\nbody'
    assert parse_frontmatter(text) == {"name": "x", "description": "a: b"}


def test_parse_requires_opening_marker():
    with pytest.raises(ValueError, match="opening"):
        parse_frontmatter("name: x\n")


def test_parse_requires_closing_marker():
    with pytest.raises(ValueError, match="closing"):
        parse_frontmatter("---\nname: x\n")


def test_validate_reports_name_mismatch(tmp_path):
    folder = _skill(tmp_path, "real", 'name: other\ndescription: "Use when x. Do NOT use y."')
    assert any("does not match" in e for e in validate_skill(folder))


def test_validate_requires_do_not_use(tmp_path):
    folder = _skill(tmp_path, "s", 'name: s\ndescription: "Use when x."')
    assert any("Do NOT use" in e for e in validate_skill(folder))


def test_validate_limits_description(tmp_path):
    long = "Use when " + "x" * MAX_DESCRIPTION + " Do NOT use y."
    folder = _skill(tmp_path, "s", f'name: s\ndescription: "{long}"')
    assert any("too long" in e for e in validate_skill(folder))


def test_validate_missing_skill_md(tmp_path):
    (tmp_path / "empty").mkdir()
    assert validate_skill(tmp_path / "empty") == ["empty: SKILL.md missing"]


@pytest.mark.parametrize("name", CORE)
def test_core_skill_is_valid(kit_root, name):
    assert validate_skill(kit_root / ".agents" / "skills" / name) == []


@pytest.mark.parametrize("name", CORE)
def test_core_skill_description_is_one_quoted_line(kit_root, name):
    text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("description:"))
    assert line.startswith('description: "') and line.endswith('"')
    assert line.count('"') == 2


@pytest.mark.parametrize("name", CORE)
def test_core_skill_has_example(kit_root, name):
    assert list((kit_root / ".agents" / "skills" / name / "examples").glob("*.md"))


@pytest.mark.parametrize("name", WITH_LANGUAGES)
def test_language_reference_exists(kit_root, name):
    assert (kit_root / ".agents" / "skills" / name / "references" / "languages.md").is_file()


def test_agents_md_policy(kit_root):
    text = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    for heading in ("## Understand the task", "## Build", "## Validate",
                    "## Optimize", "## Restrictions"):
        assert heading in text
    assert "task-router" in text
    assert "hackathon-kit:begin" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skills.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kit.skills'`.

- [ ] **Step 3: Implement the validator**

`kit/skills.py`:
```python
"""Minimal SKILL.md frontmatter parsing and validation (no YAML dependency)."""

from __future__ import annotations

from pathlib import Path

MAX_DESCRIPTION = 400


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat `key: value` block between the leading `---` lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---'")
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {line!r}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    raise ValueError("missing closing '---'")


def validate_skill(skill_dir: Path) -> list[str]:
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{name}: SKILL.md missing"]
    try:
        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return [f"{name}: {exc}"]
    errors = []
    if meta.get("name") != name:
        errors.append(f"{name}: frontmatter name '{meta.get('name')}' does not match folder")
    description = meta.get("description", "")
    if not description:
        errors.append(f"{name}: description missing")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"{name}: description too long ({len(description)} > {MAX_DESCRIPTION})")
    elif "Do NOT use" not in description:
        errors.append(f"{name}: description must say when 'Do NOT use' the skill")
    return errors
```

- [ ] **Step 4: Write `AGENTS.md`**

```markdown
# Codex Project Policy

## Understand the task
- Extract the exact requirements, constraints, and expected outputs.
- Record assumptions separately from confirmed facts.
- Choose only the skills needed for the current task.
- Start non-trivial tasks with the task-router skill; skip it for one-line fixes.

## Build
- Prefer correct, simple, reproducible solutions.
- Respect the allowed language, environment, and dependencies.

## Validate
- Test important cases and relevant boundaries.
- Run applicable tests and linters when tools are available.
- Never claim a test passed unless it actually ran successfully.

## Optimize
- Analyze algorithmic complexity and measure real bottlenecks.
- Re-run correctness tests after any optimization.

## Restrictions
- Use only the officially permitted Codex environment and models.
- No external AI model or Claude Code during the exam.
- Do not transmit task files, prompts, or outputs externally.
- No Git push, remote sync, telemetry, Computer Use, or proctoring bypass.
- Follow all official exam instructions; stop AI assistance before the written phase.
- Write TASK_BRIEF.md in the workspace only; never outside it.
```

- [ ] **Step 5: Write `task-router`**

`.agents/skills/task-router/SKILL.md`:
````markdown
---
name: task-router
description: "Use when starting a new non-trivial coding task or when requirements are unclear - extracts goal, I/O format, constraints and evaluation into TASK_BRIEF.md and picks the minimum set of other skills. Do NOT use for one-line fixes, follow-up edits on an already-briefed task, or questions that need no code."
---

# Task Router

Turn the task statement into a short written brief, then choose the fewest skills that cover it.

## Steps

1. Read the whole task statement and list every provided file. Do not write solution code yet.
2. Extract, quoting the statement where possible:
   - **Goal**: one sentence.
   - **Inputs/outputs**: formats, file names and paths, encodings, exact output layout.
   - **Constraints**: language and version, allowed libraries, input size limits, time and memory limits.
   - **Evaluation**: how the result is judged (hidden tests, exact output match, performance, review).
3. Separate facts from assumptions. Anything the statement does not say is an assumption: mark it `ASSUMPTION` and choose the most conservative reading.
4. Classify the task as one of `algorithm`, `data`, `web-api`, `output-format`, `debugging`, `other`.
5. Select skills. Add a skill only when its condition holds:

   | Condition | Skill |
   |---|---|
   | Core logic with checkable inputs and outputs | `tdd-automator` |
   | Input sizes or time/memory limits are stated, or a naive approach would be too slow | `algorithm-optimizer` |
   | There is a deliverable (files, output format, run command) | `submission-validator`, before finishing |
   | The user wants the design explained | `implementation-review` (explicit `$implementation-review` only) |
   | Measured slowness needs profiling | `benchmark` (explicit `$benchmark` only) |

6. Write `TASK_BRIEF.md` in the workspace root with the template below. Keep it under 40 lines.
7. Re-read `TASK_BRIEF.md` when the conversation gets long and before declaring the task done.

## TASK_BRIEF.md template

```markdown
# Task Brief
Type: <algorithm|data|web-api|output-format|debugging|other>

## Goal
<one sentence>

## Inputs / Outputs
- <format, files, paths, exact layout>

## Constraints
- <language, libraries, sizes, limits>

## Evaluation
- <how the result is judged>

## Facts vs assumptions
- FACT: <quoted from the statement>
- ASSUMPTION: <what you assumed and why>

## Risks
- <edge cases, ambiguities, performance traps>

## Skills
- <skill>: <why it is needed>
```

## Rules

- If an ambiguity would change the output, ask the user before building.
- Keep the brief inside the workspace. Never send task content anywhere else.
````

`.agents/skills/task-router/examples/example.md`:
````markdown
# Example: mock task to brief

Statement (mock): "Read `scores.csv` (columns `name,score`, up to 200,000 rows). Print the top 3 names by score, ties broken by name ascending, one per line. Time limit 2 s."

Resulting `TASK_BRIEF.md` (abridged):

```markdown
# Task Brief
Type: data

## Goal
Print the 3 highest-scoring names from scores.csv.

## Inputs / Outputs
- Input: scores.csv with header `name,score`
- Output: 3 lines on stdout, one name per line

## Constraints
- Up to 200,000 rows; 2 s time limit

## Facts vs assumptions
- FACT: "ties broken by name ascending"
- ASSUMPTION: scores may be non-integers (not stated); parse as float
- ASSUMPTION: with fewer than 3 rows, print all rows

## Skills
- tdd-automator: tie-breaking and short-file cases are easy to get wrong
- submission-validator: exact stdout format
```

`algorithm-optimizer` is not selected: sorting 200,000 rows is well within 2 s.
````

- [ ] **Step 6: Write `tdd-automator`**

`.agents/skills/tdd-automator/SKILL.md`:
```markdown
---
name: tdd-automator
description: "Use when implementing or fixing core logic whose results can be checked - writes failing tests first from the task's examples and relevant boundaries, then implements until they pass. Do NOT use for pure formatting, config, docs, or trivial one-line edits."
---

# TDD Automator

## Steps

1. Read `TASK_BRIEF.md` if it exists. List the behaviours the task actually checks.
2. Turn every example in the task statement into a test first. These are the most valuable tests.
3. Add boundary cases only when the input definition allows them:
   - empty or single-element input; minimum and maximum sizes and values
   - duplicates, already sorted or reverse sorted, negative numbers, zero
   - None / NaN / missing values only if the input format can contain them
   Skip cases the statement rules out.
4. Run the tests and confirm they fail for the expected reason (missing function or wrong result, not a typo).
5. Implement the smallest change that makes them pass. Run again.
6. On failure, read the assertion and fix the code. Change a test only if it contradicts the statement.
7. Keep the suite fast (about 10 s). Large-input timing belongs to the benchmark skill.

## Running tests

See `references/languages.md`. In Python prefer `python -m pytest -q`; if pytest is not available, a plain script with `assert` statements is fine.

## Reporting

- Give the exact command you ran and its result (`N passed`, or the failure).
- If tests could not run (no runner, no permission, missing dependency), say so and why.
- Never report a test as passing without running it.
```

`.agents/skills/tdd-automator/references/languages.md`:
```markdown
# Test runners by language

| Language | Runner (preferred, then fallback) | Run command |
|---|---|---|
| Python | pytest, then a plain script with `assert` | `python -m pytest -q` / `python test_x.py` |
| C++ | separate test `main` using `<cassert>` | `g++ -std=c++17 -O2 -o test_x test_x.cpp && ./test_x` |
| Java | JUnit if the project already has it, else a `main` with checks | `javac *.java && java -ea TestMain` |
| JavaScript | built-in `node:test` | `node --test` |

- Python: if `python -m pytest` says "No module named pytest", use a plain script; install packages only if the task allows it.
- C++ and Java asserts are off with `-DNDEBUG` or without `-ea`; check the flags.
- Keep test inputs synthetic.
```

`.agents/skills/tdd-automator/examples/example.md`:
````markdown
# Example: tests first for a mock task

Mock task: `longest_run(xs)` returns the length of the longest block of equal adjacent values; `0 <= len(xs) <= 100000`.

```python
# test_longest_run.py - written before solution.py exists
from solution import longest_run


def test_statement_example():
    assert longest_run([1, 1, 2, 2, 2, 1]) == 3


def test_empty():
    assert longest_run([]) == 0


def test_single():
    assert longest_run([7]) == 1


def test_all_equal():
    assert longest_run([5] * 1000) == 1000


def test_run_at_end():
    assert longest_run([1, 2, 3, 3]) == 2
```

NaN is not tested: the input is a list of ints.

`python -m pytest -q test_longest_run.py` fails with `ImportError` before `solution.py` exists and passes after it is implemented.
````

- [ ] **Step 7: Write `algorithm-optimizer`**

`.agents/skills/algorithm-optimizer/SKILL.md`:
```markdown
---
name: algorithm-optimizer
description: "Use when the task states input sizes or time/memory limits, or a working solution is too slow - estimates the allowed complexity, finds the bottleneck and compares better algorithms, re-running tests after each change. Do NOT use when inputs are small and the current solution already meets the limits."
---

# Algorithm Optimizer

## Steps

1. Find the limits: input sizes (n, m, ...), time limit, memory limit. If missing, write them as ASSUMPTION.
2. Work out the budget. Roughly 1e8 simple operations per second in C++/Java and 1e7 in Python.

   | Largest n | Target complexity |
   |---|---|
   | 10 to 12 | O(n!) or O(2^n * n) |
   | 20 to 25 | O(2^n) |
   | 500 | O(n^3) |
   | 5,000 | O(n^2) |
   | 1e5 to 1e6 | O(n log n) |
   | 1e7 and more | O(n) |

   In Python aim one row lower than this table.
3. Write the current complexity of each loop and call, and name the dominant term.
4. Pick a fix that matches the bottleneck:
   - repeated lookups: hash map or set
   - pair or range queries: sorting with two pointers or binary search, prefix sums
   - overlapping subproblems: dynamic programming or memoization
   - repeated min/max: heap
   - connectivity: union-find; shortest paths: BFS or Dijkstra
5. Avoid myths: `for` loops are fine; list comprehensions do not change complexity; use NumPy/pandas vectorization only if the library is allowed and a measurement shows a gain.
6. Change one thing at a time and re-run the correctness tests after each change.
7. Record before and after: complexity, and time on the same input if you measured it.

Language-specific speed notes are in `references/languages.md`.
```

`.agents/skills/algorithm-optimizer/references/languages.md`:
```markdown
# Performance notes by language

| Language | Notes |
|---|---|
| Python | Read input with `sys.stdin.buffer` or `sys.stdin.readline`; use `collections.deque`, `heapq`, `bisect`, `functools.lru_cache`; raise `sys.setrecursionlimit` or rewrite deep recursion as a loop; avoid string `+=` in loops (use `"".join`). |
| C++ | Compile with `-O2`; `std::ios::sync_with_stdio(false); std::cin.tie(nullptr);`; prefer `std::vector` over `std::list`; `unordered_map` can degrade on adversarial keys. |
| Java | `BufferedReader` and `StringBuilder` for I/O; avoid boxing in hot loops (`int[]` over `List<Integer>`). |
| JavaScript | Read all input at once (`fs.readFileSync(0)`); `Map`/`Set` for lookups; avoid `Array.prototype.shift` in loops (O(n)). |
```

`.agents/skills/algorithm-optimizer/examples/example.md`:
````markdown
# Example: O(n^2) to O(n)

Mock task: count pairs `i < j` with `a[i] + a[j] == k`, `n <= 200,000`, 1 s.

Before (O(n^2), about 2e10 steps at n = 200,000, too slow):

```python
def count_pairs(a, k):
    return sum(1 for i in range(len(a)) for j in range(i + 1, len(a)) if a[i] + a[j] == k)
```

After (O(n) with a hash map of counts seen so far):

```python
from collections import Counter


def count_pairs(a, k):
    seen, total = Counter(), 0
    for x in a:
        total += seen[k - x]
        seen[x] += 1
    return total
```

The same tests pass before and after; the n = 200,000 case went from timing out to well under a second.
````

- [ ] **Step 8: Write `submission-validator`**

`.agents/skills/submission-validator/SKILL.md`:
```markdown
---
name: submission-validator
description: "Use right before finishing or submitting - checks the result against every requirement in TASK_BRIEF.md or the task statement, output file names and formats, leftover debug output, and runs tests and linters, giving evidence for each item. Do NOT use mid-implementation or for tasks with no deliverable."
---

# Submission Validator

## Steps

1. Build a checklist with one row per requirement from `TASK_BRIEF.md` (or the statement if there is no brief).
2. Run the automated checks and record the exact command and result for each:
   - required files exist at the required paths with the exact names
   - the program runs with the stated command, and its output on the statement's examples matches the stated format exactly (whitespace, line endings, ordering)
   - tests pass; the linter passes if one is available
   - no leftover debug output or markers (see `references/languages.md` for search commands)
   - no hard-coded absolute paths from this machine; no unused heavy dependencies
3. List the checks only a human can do (judgement calls, visual checks, the exam's own submission step) as MANUAL. Do not mark them as passed.
4. Output a table: `Requirement | Check | Evidence | Result` with Result one of PASS, FAIL, MANUAL.
5. If anything FAILs, fix it and re-run only the affected checks, then re-print the table.

## Rules

- Never click submission buttons or operate a browser. The human submits.
- Never report PASS without the command output that shows it.
```

`.agents/skills/submission-validator/references/languages.md`:
```markdown
# Validation commands by language

| Language | Debug-output search | Lint / static check |
|---|---|---|
| Python | `grep -rnE "print\(|breakpoint\(|pdb\.set_trace|TODO|FIXME" --include=*.py .` | `ruff check .` (if installed), `python -m py_compile <files>` |
| C++ | `grep -rnE "cerr|printf\(\"DEBUG|TODO|FIXME" --include=*.cpp .` | `g++ -std=c++17 -Wall -Wextra -fsyntax-only <files>` |
| Java | `grep -rnE "System\.(out|err)\.print|TODO|FIXME" --include=*.java .` | `javac -Xlint:all *.java` |
| JavaScript | `grep -rnE "console\.(log|debug)|debugger|TODO|FIXME" --include=*.js .` | `node --check <file>` |

On Windows PowerShell use `Select-String -Path <glob> -Pattern '<regex>'` instead of `grep`.
`print` is legitimate when it produces the required output: check each hit, do not delete blindly.
```

`.agents/skills/submission-validator/examples/example.md`:
```markdown
# Example: validation table

Mock task: "Write `solution.py` that reads `input.txt` and writes `output.txt` with one integer per line."

| Requirement | Check | Evidence | Result |
|---|---|---|---|
| File named `solution.py` at the root | `ls solution.py` | file listed | PASS |
| Writes `output.txt`, one integer per line | `python solution.py && python -c "[int(l) for l in open('output.txt')]"` | exit 0, no ValueError | PASS |
| Matches the statement example | `python solution.py` on the example, then `diff output.txt expected.txt` | no diff | PASS |
| No debug prints | `grep -n "print(" solution.py` | 1 hit, line 40 writes the result | PASS |
| Tests pass | `python -m pytest -q` | `6 passed` | PASS |
| Submitted through the exam page | human step | - | MANUAL |
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `uv run pytest tests/test_skills.py -q`
Expected: all passed. If a description is too long, shorten the wording (keep "Use when" first and "Do NOT use" present).

- [ ] **Step 10: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add AGENTS.md kit/skills.py tests/test_skills.py .agents
git commit -m "feat: add AGENTS.md policy, skill validator and four core skills"
```

---

### Task 5: Auxiliary skills (explicit invocation only)

**Files:**
- Create: `.agents/skills/implementation-review/SKILL.md`, `.../agents/openai.yaml`, `.../examples/example.md`
- Create: `.agents/skills/benchmark/SKILL.md`, `.../agents/openai.yaml`, `.../references/languages.md`, `.../examples/example.md`
- Modify: `tests/test_skills.py`

**Interfaces:**
- Consumes: `kit.skills.validate_skill`, `parse_frontmatter`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_skills.py`:
```python
ALL = CORE + ["implementation-review", "benchmark"]
EXPLICIT_ONLY = ["implementation-review", "benchmark"]


@pytest.mark.parametrize("name", ALL)
def test_every_skill_is_valid(kit_root, name):
    assert validate_skill(kit_root / ".agents" / "skills" / name) == []


def test_skill_set_matches_folders(kit_root):
    folders = sorted(p.name for p in (kit_root / ".agents" / "skills").iterdir() if p.is_dir())
    assert folders == sorted(ALL)


def test_total_description_budget(kit_root):
    total = 0
    for name in ALL:
        text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        total += len(parse_frontmatter(text)["description"])
    assert total <= 2000, total


@pytest.mark.parametrize("name", EXPLICIT_ONLY)
def test_explicit_only_policy(kit_root, name):
    yaml_text = (kit_root / ".agents" / "skills" / name / "agents" / "openai.yaml").read_text(
        encoding="utf-8")
    assert "allow_implicit_invocation: false" in yaml_text
    text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    assert parse_frontmatter(text)["description"].startswith("Use only when explicitly invoked")


def test_benchmark_language_reference(kit_root):
    assert (kit_root / ".agents/skills/benchmark/references/languages.md").is_file()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skills.py -q`
Expected: FAIL — `implementation-review: SKILL.md missing` and missing folders.

- [ ] **Step 3: Write `implementation-review`**

`.agents/skills/implementation-review/SKILL.md`:
````markdown
---
name: implementation-review
description: "Use only when explicitly invoked as $implementation-review - summarizes why the current solution works: key branches, data structure choices, correctness argument, complexity and limits, for the implementer's own understanding. Do NOT use automatically, and never during the written-answer phase."
---

# Implementation Review

Explain the solution so the implementer understands it. This is explanation only; it does not change behaviour.

## Steps

1. Read the solution and `TASK_BRIEF.md` if present.
2. Write the summary with this template, at most 25 lines:

```markdown
## How it works
- <the core idea in 1-2 lines>

## Key decisions
- <branch or data structure>: <why, and what the alternative would cost>

## Why it is correct
- <invariant or argument; mention the boundary cases covered by tests>

## Complexity
- Time: O(...)  Space: O(...)  (n = ...)

## Limits
- <inputs or situations where it would fail or slow down>
```

3. Add comments only to functions that are hard to follow, one or two lines each. Do not comment every line.

## Rules

- The written-answer phase of the exam forbids AI help. Stop using this skill and all AI assistance before it starts. Never draft, paste or submit written answers.
````

`.agents/skills/implementation-review/agents/openai.yaml`:
```yaml
policy:
  allow_implicit_invocation: false
```

`.agents/skills/implementation-review/examples/example.md`:
```markdown
# Example: review of the mock pair-count solution

## How it works
- One pass; for each x, add how many earlier values equal k - x.

## Key decisions
- Counter of seen values: O(1) lookups; sorting with two pointers would be O(n log n) and needs extra care for duplicates.

## Why it is correct
- Each pair (i, j) with i < j is counted exactly once, when j is visited. Tests cover duplicates, an empty list and no pairs.

## Complexity
- Time: O(n)  Space: O(n)  (n = len(a))

## Limits
- Memory grows with the number of distinct values.
```

- [ ] **Step 4: Write `benchmark`**

`.agents/skills/benchmark/SKILL.md`:
````markdown
---
name: benchmark
description: "Use only when explicitly invoked as $benchmark - measures runtime or memory on synthetic inputs with standard tools (timeit, cProfile, tracemalloc) and compares before and after under the same conditions. Do NOT use automatically or when tests already show the solution is fast enough."
---

# Benchmark

## Steps

1. Generate synthetic input at the stated maximum size with a fixed random seed. Never use real task data from outside the workspace.
2. Measure wall time first (Python shown; other languages in `references/languages.md`):

```python
import random
import timeit

random.seed(0)
data = [random.randint(-10**9, 10**9) for _ in range(200_000)]
print(min(timeit.repeat(lambda: solve(data), number=1, repeat=5)))
```

3. Only if it is too slow, find where the time goes:

```python
import cProfile
import pstats

cProfile.run("solve(data)", "prof.out")
pstats.Stats("prof.out").sort_stats("cumulative").print_stats(10)
```

4. Only if memory is the problem:

```python
import tracemalloc

tracemalloc.start()
solve(data)
print(tracemalloc.get_traced_memory())  # (current, peak) in bytes
tracemalloc.stop()
```

5. After a change, re-run the correctness tests, then the same measurement with the same seed and size.
6. Report a table: `Version | Input size | Best of 5 (s) | Peak memory`. Note noise: other processes, first-run warm-up, timer resolution.

## Rules

- Delete temporary profiling files (such as `prof.out`) before submitting.
````

`.agents/skills/benchmark/agents/openai.yaml`:
```yaml
policy:
  allow_implicit_invocation: false
```

`.agents/skills/benchmark/references/languages.md`:
```markdown
# Timing by language

| Language | Wall time | Profiling | Memory |
|---|---|---|---|
| Python | `timeit.repeat` (best of 5) | `cProfile` + `pstats` | `tracemalloc` |
| C++ | `std::chrono::steady_clock` around the call, build with `-O2` | `perf` or `gprof` if installed | `/usr/bin/time -v` (Linux) |
| Java | `System.nanoTime()` after a warm-up run | JDK Flight Recorder (`-XX:StartFlightRecording`) if allowed | `Runtime.getRuntime()` totals |
| JavaScript | `performance.now()` | `node --cpu-prof` | `process.memoryUsage()` |

Use the same machine, input, seed and build flags for before and after.
```

`.agents/skills/benchmark/examples/example.md`:
```markdown
# Example: before and after

Mock: `count_pairs` from the algorithm-optimizer example, n = 200,000, seed 0.

| Version | Input size | Best of 5 (s) | Peak memory |
|---|---|---|---|
| nested loops | 2,000 | 0.21 | 0.1 MB |
| nested loops | 200,000 | stopped after 60 s | - |
| Counter | 200,000 | 0.05 | 12 MB |

Noise: laptop on battery; numbers vary by about 10% between runs.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_skills.py -q`
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add .agents tests/test_skills.py
git commit -m "feat: add explicit-only implementation-review and benchmark skills"
```

---

### Task 6: Safe filesystem operations and AGENTS.md block merge

**Files:**
- Create: `kit/fsops.py`, `kit/agentsmd.py`, `tests/test_fsops.py`, `tests/test_agentsmd.py`

**Interfaces:**
- Consumes: `kit.model.Outcome`.
- Produces: `kit.fsops.STATE_REL = ".kit/state.json"`; `class PathEscapeError(Exception)`; `safe_path(root: Path, rel: str) -> Path`; `sha256(data: bytes) -> str`; `timestamp() -> str` (`YYYYmmdd-HHMMSS`); `class State` with attribute `files: dict[str, str]`, `State.load(target: Path) -> State`, `state.save(target: Path, profile: str) -> None` (deterministic bytes); `backup_file(target: Path, rel: str, stamp: str) -> Path` (copies to `.kit/backups/<stamp>/<rel>`).
- Produces: `kit.agentsmd.BEGIN`, `END`; `class MarkerError(ValueError)`; `render_block(body: str) -> str`; `extract_block(text: str) -> tuple[int, int, str] | None` (start, stop, stripped interior; raises `MarkerError`); `merge(existing: str | None, body: str, recorded_hash: str | None) -> tuple[str | None, str, str]` returning (new text or None, an `Outcome` value, detail). The recorded hash is `sha256(body.strip().encode("utf-8"))`.

- [ ] **Step 1: Write the failing tests**

`tests/test_fsops.py`:
```python
import pytest

from kit.fsops import PathEscapeError, State, backup_file, safe_path, sha256


def test_safe_path_inside(tmp_path):
    assert safe_path(tmp_path, "a/b.txt") == (tmp_path / "a" / "b.txt").resolve()


@pytest.mark.parametrize("rel", ["../x", "a/../../x"])
def test_safe_path_rejects_parent_traversal(tmp_path, rel):
    with pytest.raises(PathEscapeError):
        safe_path(tmp_path, rel)


def test_safe_path_rejects_absolute_outside(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(PathEscapeError):
        safe_path(root, str(tmp_path / "elsewhere.txt"))


def test_safe_path_rejects_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not permitted on this system")
    with pytest.raises(PathEscapeError):
        safe_path(root, "link/x.txt")


def test_state_roundtrip(tmp_path):
    State({"a.txt": "1"}).save(tmp_path, "core")
    assert State.load(tmp_path).files == {"a.txt": "1"}


def test_state_save_is_deterministic(tmp_path):
    State({"b": "2", "a": "1"}).save(tmp_path, "core")
    first = (tmp_path / ".kit" / "state.json").read_bytes()
    State({"a": "1", "b": "2"}).save(tmp_path, "core")
    assert (tmp_path / ".kit" / "state.json").read_bytes() == first


def test_state_load_corrupt_returns_empty(tmp_path):
    (tmp_path / ".kit").mkdir()
    (tmp_path / ".kit" / "state.json").write_text("{", encoding="utf-8")
    assert State.load(tmp_path).files == {}


def test_backup_copies_into_stamp_dir(tmp_path):
    (tmp_path / "AGENTS.md").write_bytes(b"original")
    dst = backup_file(tmp_path, "AGENTS.md", "20261028-120000")
    assert dst == (tmp_path / ".kit/backups/20261028-120000/AGENTS.md").resolve()
    assert dst.read_bytes() == b"original"


def test_sha256_known_value():
    assert sha256(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
```

`tests/test_agentsmd.py`:
```python
import pytest

from kit.agentsmd import BEGIN, END, MarkerError, extract_block, merge, render_block
from kit.fsops import sha256

BODY = "# Policy\n- rule one\n"


def test_render_block_wraps_stripped_body():
    assert render_block(BODY) == f"{BEGIN}\n# Policy\n- rule one\n{END}\n"


def test_merge_creates_when_missing():
    text, outcome, _ = merge(None, BODY, None)
    assert outcome == "create" and text == render_block(BODY)


def test_merge_creates_when_blank():
    text, outcome, _ = merge(" \n", BODY, None)
    assert outcome == "create" and text == render_block(BODY)


def test_merge_appends_and_preserves_existing_bytes():
    existing = "# Team rules\r\nKeep CRLF.\r\n"
    text, outcome, _ = merge(existing, BODY, None)
    assert outcome == "append"
    assert text == existing + "\n" + render_block(BODY)


def test_merge_appends_newline_when_missing():
    text, outcome, _ = merge("no newline", BODY, None)
    assert outcome == "append"
    assert text == "no newline\n\n" + render_block(BODY)


def test_merge_unchanged_when_block_matches():
    text, outcome, _ = merge("intro\n\n" + render_block(BODY), BODY, None)
    assert outcome == "unchanged" and text is None


def test_merge_updates_block_written_by_kit():
    old = "# Policy\n- old rule\n"
    existing = "intro\n\n" + render_block(old) + "outro\n"
    text, outcome, _ = merge(existing, BODY, sha256(old.strip().encode("utf-8")))
    assert outcome == "update"
    assert text == "intro\n\n" + render_block(BODY) + "outro\n"


def test_merge_updates_block_with_crlf_after_end_marker():
    old = "old"
    existing = f"{BEGIN}\r\nold\r\n{END}\r\ntail\r\n"
    text, outcome, _ = merge(existing, BODY, sha256(old.encode("utf-8")))
    assert outcome == "update"
    assert text == render_block(BODY) + "tail\r\n"


def test_merge_conflict_when_user_edited_block():
    existing = render_block("# Policy\n- user changed this\n")
    text, outcome, detail = merge(existing, BODY, sha256(b"something else"))
    assert outcome == "conflict" and text is None and "edited" in detail


def test_merge_conflict_when_block_has_no_record():
    _, outcome, _ = merge(render_block("different"), BODY, None)
    assert outcome == "conflict"


@pytest.mark.parametrize("text", [
    f"{BEGIN}\nx\n",
    f"x\n{END}\n",
    f"{END}\n{BEGIN}\n",
    f"{BEGIN}\n{BEGIN}\n{END}\n",
])
def test_malformed_markers(text):
    with pytest.raises(MarkerError):
        extract_block(text)
    assert merge(text, BODY, None)[1] == "conflict"


def test_extract_block_none_without_markers():
    assert extract_block("plain\n") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_fsops.py tests/test_agentsmd.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kit.fsops'`.

- [ ] **Step 3: Implement**

`kit/fsops.py`:
```python
"""Filesystem helpers: confined paths, hashing, kit state and backups."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

STATE_REL = ".kit/state.json"


class PathEscapeError(Exception):
    """A path resolved outside the target workspace."""


def safe_path(root: Path, rel: str) -> Path:
    """Resolve rel under root, refusing anything (.., absolute, symlink) that escapes it."""
    root = root.resolve()
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise PathEscapeError(f"refusing path outside target: {rel}")
    return candidate


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


class State:
    """Hashes of files the kit wrote, so re-runs can tell kit edits from user edits."""

    def __init__(self, files: dict[str, str] | None = None):
        self.files = dict(files or {})

    @classmethod
    def load(cls, target: Path) -> State:
        path = target / STATE_REL
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        files = data.get("files", {}) if isinstance(data, dict) else {}
        return cls(files if isinstance(files, dict) else {})

    def save(self, target: Path, profile: str) -> None:
        path = safe_path(target, STATE_REL)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "profile": profile, "files": dict(sorted(self.files.items()))}
        path.write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def backup_file(target: Path, rel: str, stamp: str) -> Path:
    src = safe_path(target, rel)
    dst = safe_path(target, f".kit/backups/{stamp}/{rel}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst
```

`kit/agentsmd.py`:
```python
"""Merge the kit policy into AGENTS.md inside a protected block, never touching other text."""

from __future__ import annotations

from .fsops import sha256
from .model import Outcome

BEGIN = "<!-- hackathon-kit:begin -->"
END = "<!-- hackathon-kit:end -->"


class MarkerError(ValueError):
    """Protected-block markers are missing a partner, duplicated or out of order."""


def render_block(body: str) -> str:
    return f"{BEGIN}\n{body.strip()}\n{END}\n"


def extract_block(text: str) -> tuple[int, int, str] | None:
    """Return (start, stop, stripped interior) of the block, or None if there is none."""
    begins, ends = text.count(BEGIN), text.count(END)
    if begins == 0 and ends == 0:
        return None
    if begins != 1 or ends != 1:
        raise MarkerError("expected exactly one begin and one end marker")
    start, end = text.index(BEGIN), text.index(END)
    if end < start:
        raise MarkerError("end marker appears before begin marker")
    stop = end + len(END)
    if text.startswith("\r\n", stop):
        stop += 2
    elif text.startswith("\n", stop):
        stop += 1
    return start, stop, text[start + len(BEGIN):end].strip()


def merge(existing: str | None, body: str,
          recorded_hash: str | None) -> tuple[str | None, str, str]:
    """Return (new text or None when nothing is written, outcome, detail)."""
    block = render_block(body)
    if existing is None or not existing.strip():
        return block, Outcome.CREATE, ""
    try:
        found = extract_block(existing)
    except MarkerError as exc:
        return None, Outcome.CONFLICT, str(exc)
    if found is None:
        sep = "" if existing.endswith("\n") else "\n"
        return existing + sep + "\n" + block, Outcome.APPEND, ""
    start, stop, interior = found
    if interior == body.strip():
        return None, Outcome.UNCHANGED, ""
    if recorded_hash is not None and sha256(interior.encode("utf-8")) == recorded_hash:
        return existing[:start] + block + existing[stop:], Outcome.UPDATE, ""
    return None, Outcome.CONFLICT, "kit block was edited outside the kit"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_fsops.py tests/test_agentsmd.py -q`
Expected: all passed (symlink test may be SKIPPED on Windows without developer mode).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add kit/fsops.py kit/agentsmd.py tests/test_fsops.py tests/test_agentsmd.py
git commit -m "feat: add confined paths, kit state, backups and AGENTS.md block merge"
```

---

### Task 7: Change planner

**Files:**
- Create: `kit/plan.py`, `tests/test_plan.py`

**Interfaces:**
- Consumes: `kit.agentsmd.merge`; `kit.fsops.State`, `safe_path`, `sha256`, `PathEscapeError`; `kit.profiles.Profile`; `kit.model.Outcome`.
- Produces: `kit.plan.FileChange(rel: str, owner: str, outcome: str, data: bytes | None = None, record: str | None = None, detail: str = "")` — `owner` is `"AGENTS.md"` or `"skill:<name>"`; `record` is the hash to store in state after applying (None for conflicts).
- Produces: `iter_skill_files(kit_root: Path, name: str) -> list[tuple[str, bytes]]` (rel paths like `.agents/skills/<name>/SKILL.md`, sorted); `plan_agents_md(target: Path, kit_root: Path, state: State) -> FileChange`; `plan_file(target: Path, rel: str, owner: str, data: bytes, state: State) -> FileChange`; `plan_changes(target: Path, kit_root: Path, profile: Profile, state: State) -> list[FileChange]` (AGENTS.md first, then skill files in profile order); `format_plan(changes: list[FileChange], verbose: bool = False) -> str` (ends with a line starting `Summary:      ` listing counts in `Outcome.ALL` order, e.g. `0 create, 0 update, 0 append, 0 conflict, 25 unchanged`).

- [ ] **Step 1: Write the failing tests**

`tests/test_plan.py`:
```python
from kit.fsops import State, sha256
from kit.model import Outcome
from kit.plan import FileChange, format_plan, plan_changes, plan_file
from kit.profiles import load_profile

REL = ".agents/skills/task-router/SKILL.md"


def test_fresh_workspace_plans_creates(kit_root, workspace):
    changes = plan_changes(workspace, kit_root, load_profile(kit_root, "core"), State())
    assert changes[0].rel == "AGENTS.md"
    assert all(c.outcome == Outcome.CREATE for c in changes)
    assert REL in {c.rel for c in changes}
    owners = {c.owner for c in changes}
    assert "skill:benchmark" in owners and "AGENTS.md" in owners


def test_identical_file_is_unchanged_and_recorded(kit_root, workspace):
    data = (kit_root / REL).read_bytes()
    (workspace / REL).parent.mkdir(parents=True)
    (workspace / REL).write_bytes(data)
    change = plan_file(workspace, REL, "skill:task-router", data, State())
    assert change.outcome == Outcome.UNCHANGED
    assert change.data is None and change.record == sha256(data)


def test_kit_written_file_is_updated(workspace):
    (workspace / "f.txt").write_bytes(b"old")
    change = plan_file(workspace, "f.txt", "o", b"new", State({"f.txt": sha256(b"old")}))
    assert change.outcome == Outcome.UPDATE and change.data == b"new"


def test_user_modified_file_conflicts(workspace):
    (workspace / "f.txt").write_bytes(b"user edit")
    change = plan_file(workspace, "f.txt", "o", b"new", State({"f.txt": sha256(b"old")}))
    assert change.outcome == Outcome.CONFLICT and change.record is None


def test_unrecorded_different_file_conflicts(workspace):
    (workspace / "f.txt").write_bytes(b"someone else's")
    assert plan_file(workspace, "f.txt", "o", b"new", State()).outcome == Outcome.CONFLICT


def test_directory_in_place_of_file_conflicts(workspace):
    (workspace / "f.txt").mkdir()
    assert plan_file(workspace, "f.txt", "o", b"new", State()).outcome == Outcome.CONFLICT


def test_escaping_path_conflicts(workspace):
    change = plan_file(workspace, "../evil.txt", "o", b"x", State())
    assert change.outcome == Outcome.CONFLICT and "outside" in change.detail


def test_existing_agents_md_is_appended(kit_root, workspace):
    (workspace / "AGENTS.md").write_text("# Mine\n", encoding="utf-8")
    changes = plan_changes(workspace, kit_root, load_profile(kit_root, "core"), State())
    assert changes[0].outcome == Outcome.APPEND


def test_non_utf8_agents_md_conflicts(kit_root, workspace):
    (workspace / "AGENTS.md").write_bytes(b"\xff\xfe\x00bad")
    changes = plan_changes(workspace, kit_root, load_profile(kit_root, "core"), State())
    assert changes[0].outcome == Outcome.CONFLICT and "UTF-8" in changes[0].detail


def test_format_plan_hides_unchanged_unless_verbose():
    changes = [FileChange("a", "o", Outcome.CREATE), FileChange("b", "o", Outcome.UNCHANGED)]
    short = format_plan(changes)
    assert "CREATE" in short and "  UNCHANGED" not in short
    assert short.splitlines()[-1] == (
        "Summary:      1 create, 0 update, 0 append, 0 conflict, 1 unchanged")
    assert "UNCHANGED b" in format_plan(changes, verbose=True)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_plan.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kit.plan'`.

- [ ] **Step 3: Implement**

`kit/plan.py`:
```python
"""Decide, without writing anything, what should happen to each kit file in the target."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import agentsmd
from .fsops import PathEscapeError, State, safe_path, sha256
from .model import Outcome
from .profiles import Profile


@dataclass
class FileChange:
    rel: str
    owner: str
    outcome: str
    data: bytes | None = None
    record: str | None = None
    detail: str = ""


def iter_skill_files(kit_root: Path, name: str) -> list[tuple[str, bytes]]:
    src = kit_root / ".agents" / "skills" / name
    return [
        (f".agents/skills/{name}/{path.relative_to(src).as_posix()}", path.read_bytes())
        for path in sorted(src.rglob("*"))
        if path.is_file()
    ]


def plan_agents_md(target: Path, kit_root: Path, state: State) -> FileChange:
    rel = owner = "AGENTS.md"
    body = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    try:
        path = safe_path(target, rel)
        existing = path.read_bytes().decode("utf-8") if path.is_file() else None
    except PathEscapeError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=str(exc))
    except UnicodeDecodeError:
        return FileChange(rel, owner, Outcome.CONFLICT, detail="existing AGENTS.md is not UTF-8")
    text, outcome, detail = agentsmd.merge(existing, body, state.files.get(rel))
    if outcome == Outcome.CONFLICT:
        return FileChange(rel, owner, outcome, detail=detail)
    data = text.encode("utf-8") if text is not None else None
    return FileChange(rel, owner, outcome, data, sha256(body.strip().encode("utf-8")), detail)


def plan_file(target: Path, rel: str, owner: str, data: bytes, state: State) -> FileChange:
    try:
        path = safe_path(target, rel)
    except PathEscapeError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=str(exc))
    new_hash = sha256(data)
    if not path.exists():
        return FileChange(rel, owner, Outcome.CREATE, data, new_hash)
    if not path.is_file():
        return FileChange(rel, owner, Outcome.CONFLICT, detail="exists but is not a regular file")
    current = sha256(path.read_bytes())
    if current == new_hash:
        return FileChange(rel, owner, Outcome.UNCHANGED, None, new_hash)
    if state.files.get(rel) == current:
        return FileChange(rel, owner, Outcome.UPDATE, data, new_hash)
    return FileChange(rel, owner, Outcome.CONFLICT,
                      detail="differs from the kit copy and was not written by the kit")


def plan_changes(target: Path, kit_root: Path, profile: Profile,
                 state: State) -> list[FileChange]:
    changes = [plan_agents_md(target, kit_root, state)]
    for name in profile.skills:
        for rel, data in iter_skill_files(kit_root, name):
            changes.append(plan_file(target, rel, f"skill:{name}", data, state))
    return changes


def format_plan(changes: list[FileChange], verbose: bool = False) -> str:
    counts = dict.fromkeys(Outcome.ALL, 0)
    lines = []
    for change in changes:
        counts[change.outcome] += 1
        if change.outcome == Outcome.UNCHANGED and not verbose:
            continue
        suffix = f"  ({change.detail})" if change.detail else ""
        lines.append(f"  {change.outcome.upper():<9} {change.rel}{suffix}")
    lines.append("Summary:      " + ", ".join(f"{counts[o]} {o}" for o in Outcome.ALL))
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_plan.py -q`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add kit/plan.py tests/test_plan.py
git commit -m "feat: add change planner with conflict detection"
```

---

### Task 8: Apply, verify and report

**Files:**
- Create: `kit/register.py`, `kit/verify.py`, `kit/report.py`, `tests/test_register.py`, `tests/test_verify.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: `FileChange`, `plan_changes`, `iter_skill_files` (plan); `State`, `safe_path`, `backup_file` (fsops); `extract_block`, `MarkerError` (agentsmd); `validate_skill` (skills); `Options` (cli); `EnvReport` (preflight); `Profile`.
- Produces: `kit.register.apply_changes(target: Path, changes: list[FileChange], state: State, stamp: str, profile_name: str) -> list[Path]` (returns backup paths; saves state even when a write raises; removes its `*.kit-tmp` file on failure).
- Produces: `kit.verify.verify_target(target: Path, kit_root: Path, profile: Profile, changes: list[FileChange], check_writable: bool, writable: bool) -> list[ItemResult]` — order: `"target writable"` (only if `check_writable`), `"AGENTS.md"`, then `"skill:<name>"` in profile order.
- Produces: `kit.report.overall_status(items: list[ItemResult], shell_fallback: bool = False) -> tuple[str, int]`; `next_actions(items: list[ItemResult], target: Path, status: str) -> list[str]` (≤ 3); `render(env: EnvReport, opts: Options, items: list[ItemResult], status: str, actions: list[str]) -> str` (contains lines starting `Status:       ` and `Codex load:   UNVERIFIED`).

- [ ] **Step 1: Write the failing tests**

`tests/test_register.py`:
```python
import os

import pytest

from kit.fsops import State, sha256
from kit.model import Outcome
from kit.plan import FileChange
from kit.register import apply_changes


def test_apply_creates_files_and_records_state(workspace):
    change = FileChange("a/b.txt", "o", Outcome.CREATE, b"hi\n", sha256(b"hi\n"))
    apply_changes(workspace, [change], State(), "s1", "core")
    assert (workspace / "a" / "b.txt").read_bytes() == b"hi\n"
    assert State.load(workspace).files == {"a/b.txt": sha256(b"hi\n")}


def test_apply_backs_up_before_update(workspace):
    (workspace / "a.txt").write_bytes(b"old")
    change = FileChange("a.txt", "o", Outcome.UPDATE, b"new", sha256(b"new"))
    backups = apply_changes(workspace, [change], State(), "s1", "core")
    assert (workspace / "a.txt").read_bytes() == b"new"
    assert [b.read_bytes() for b in backups] == [b"old"]


def test_apply_leaves_conflicts_alone(workspace):
    (workspace / "a.txt").write_bytes(b"user")
    apply_changes(workspace, [FileChange("a.txt", "o", Outcome.CONFLICT)], State(), "s1", "core")
    assert (workspace / "a.txt").read_bytes() == b"user"
    assert State.load(workspace).files == {}


def test_apply_records_unchanged_without_writing(workspace):
    (workspace / "a.txt").write_bytes(b"same")
    change = FileChange("a.txt", "o", Outcome.UNCHANGED, None, sha256(b"same"))
    apply_changes(workspace, [change], State(), "s1", "core")
    assert State.load(workspace).files == {"a.txt": sha256(b"same")}
    assert not (workspace / ".kit" / "backups").exists()


def test_apply_cleans_temp_file_and_saves_state_on_failure(workspace, monkeypatch):
    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    change = FileChange("a.txt", "o", Outcome.CREATE, b"x", sha256(b"x"))
    with pytest.raises(OSError, match="disk full"):
        apply_changes(workspace, [change], State(), "s1", "core")
    assert not list(workspace.rglob("*.kit-tmp"))
    assert (workspace / ".kit" / "state.json").is_file()
```

`tests/test_verify.py`:
```python
import shutil

from kit.fsops import State
from kit.model import CONFLICT, FAIL, PASS, Outcome
from kit.plan import FileChange, plan_changes
from kit.profiles import load_profile
from kit.register import apply_changes
from kit.verify import verify_target

REQUIRED = {"target writable", "AGENTS.md", "skill:task-router", "skill:tdd-automator",
            "skill:algorithm-optimizer", "skill:submission-validator"}


def _install(kit_root, workspace):
    profile = load_profile(kit_root, "core")
    apply_changes(workspace, plan_changes(workspace, kit_root, profile, State()), State(),
                  "s", "core")
    return profile


def _by_name(items):
    return {item.name: item for item in items}


def test_fresh_install_verifies(kit_root, workspace):
    profile = _install(kit_root, workspace)
    items = verify_target(workspace, kit_root, profile, [], check_writable=True, writable=True)
    assert [i.name for i in items][:2] == ["target writable", "AGENTS.md"]
    assert len(items) == 8
    assert all(i.verified == PASS for i in items)
    assert {i.name for i in items if i.required} == REQUIRED


def test_missing_optional_skill_fails(kit_root, workspace):
    profile = _install(kit_root, workspace)
    shutil.rmtree(workspace / ".agents" / "skills" / "benchmark")
    item = _by_name(verify_target(workspace, kit_root, profile, [], True, True))["skill:benchmark"]
    assert item.verified == FAIL and not item.required and "not installed" in item.detail


def test_changed_skill_file_fails(kit_root, workspace):
    profile = _install(kit_root, workspace)
    skill_md = workspace / ".agents/skills/task-router/SKILL.md"
    skill_md.write_bytes(skill_md.read_bytes() + b"\nextra\n")
    item = _by_name(verify_target(workspace, kit_root, profile, [], True, True))[
        "skill:task-router"]
    assert item.verified == FAIL and "differ" in item.detail


def test_conflict_from_plan_is_reported(kit_root, workspace):
    profile = _install(kit_root, workspace)
    changes = [FileChange(".agents/skills/task-router/SKILL.md", "skill:task-router",
                          Outcome.CONFLICT, detail="edited by user")]
    item = _by_name(verify_target(workspace, kit_root, profile, changes, True, True))[
        "skill:task-router"]
    assert item.verified == CONFLICT and "edited by user" in item.detail


def test_agents_md_without_block_fails(kit_root, workspace):
    profile = _install(kit_root, workspace)
    (workspace / "AGENTS.md").write_text("# replaced\n", encoding="utf-8")
    item = _by_name(verify_target(workspace, kit_root, profile, [], True, True))["AGENTS.md"]
    assert item.verified == FAIL and "missing" in item.detail


def test_writable_item_omitted_when_not_checked(kit_root, workspace):
    profile = _install(kit_root, workspace)
    items = verify_target(workspace, kit_root, profile, [], check_writable=False, writable=False)
    assert "target writable" not in _by_name(items)
```

`tests/test_report.py`:
```python
from pathlib import Path

from kit.cli import Options
from kit.model import CONFLICT, FAIL, PASS, UNVERIFIED, ItemResult
from kit.preflight import EnvReport, ToolInfo
from kit.report import next_actions, overall_status, render


def item(name, required, verified, detail=""):
    return ItemResult(name, required, True, True, verified, detail)


def test_all_pass_is_ready():
    assert overall_status([item("a", True, PASS), item("b", False, PASS)]) == ("READY", 0)


def test_unverified_does_not_block():
    assert overall_status([item("a", True, UNVERIFIED)]) == ("READY", 0)


def test_optional_failure_is_partial():
    assert overall_status([item("a", True, PASS), item("b", False, FAIL)]) == ("PARTIAL", 1)


def test_optional_conflict_is_partial():
    assert overall_status([item("a", True, PASS), item("b", False, CONFLICT)]) == ("PARTIAL", 1)


def test_required_failure_is_blocked():
    assert overall_status([item("a", True, FAIL), item("b", False, PASS)]) == ("BLOCKED", 2)


def test_required_conflict_is_blocked():
    assert overall_status([item("a", True, CONFLICT)]) == ("BLOCKED", 2)


def test_shell_fallback_is_partial():
    assert overall_status([item("a", True, PASS)], shell_fallback=True) == ("PARTIAL", 1)


def test_next_actions_ready_points_to_skills_check(tmp_path):
    actions = next_actions([item("a", True, PASS)], tmp_path, "READY")
    assert actions == [f"Open Codex in {tmp_path} and run /skills to confirm the kit skills load."]


def test_next_actions_capped_at_three(tmp_path):
    items = [item(f"skill:{n}", True, FAIL, "not installed") for n in "abcd"]
    actions = next_actions(items, tmp_path, "BLOCKED")
    assert len(actions) == 3 and actions[0].startswith("Fix skill:a")


def test_render_contains_report_fields(tmp_path):
    env = EnvReport("Linux 6", "x86_64", "bash", "3.12.0", True,
                    {"git": ToolInfo("git", "/usr/bin/git", "git 2.0"), "uv": ToolInfo("uv")})
    opts = Options("core", tmp_path, False, False, False, False, False)
    items = [item("AGENTS.md", True, PASS), item("skill:x", True, PASS),
             item("skill:y", False, FAIL, "not installed")]
    text = render(env, opts, items, "PARTIAL", ["do this"])
    assert "Tools:        git OK, uv missing" in text
    assert "AGENTS.md:    INSTALLED" in text
    assert "Skills:       2 expected / 1 verified" in text
    assert "Codex load:   UNVERIFIED (open Codex and run /skills)" in text
    assert "  FAIL       optional skill:y  (not installed)" in text
    assert "Status:       PARTIAL" in text
    assert text.rstrip().endswith("  - do this")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_register.py tests/test_verify.py tests/test_report.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kit.register'`.

- [ ] **Step 3: Implement**

`kit/register.py`:
```python
"""Apply planned changes: atomic writes, backups before replacing, state saved even on failure."""

from __future__ import annotations

import os
from pathlib import Path

from .fsops import State, backup_file, safe_path
from .model import Outcome
from .plan import FileChange

WRITES = (Outcome.CREATE, Outcome.UPDATE, Outcome.APPEND)


def apply_changes(target: Path, changes: list[FileChange], state: State, stamp: str,
                  profile_name: str) -> list[Path]:
    backups = []
    try:
        for change in changes:
            if change.outcome in (Outcome.UPDATE, Outcome.APPEND):
                backups.append(backup_file(target, change.rel, stamp))
            if change.outcome in WRITES and change.data is not None:
                _write_atomic(safe_path(target, change.rel), change.data)
            if change.record is not None:
                state.files[change.rel] = change.record
    finally:
        state.save(target, profile_name)
    return backups


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".kit-tmp")
    tmp.write_bytes(data)
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```

`kit/verify.py`:
```python
"""Check what is actually in the target, item by item. Codex loading itself is not observable."""

from __future__ import annotations

from pathlib import Path

from .agentsmd import MarkerError, extract_block
from .model import CONFLICT, FAIL, PASS, ItemResult, Outcome
from .plan import FileChange, iter_skill_files
from .profiles import Profile
from .skills import validate_skill


def verify_target(target: Path, kit_root: Path, profile: Profile, changes: list[FileChange],
                  check_writable: bool, writable: bool) -> list[ItemResult]:
    conflicts: dict[str, str] = {}
    for change in changes:
        if change.outcome == Outcome.CONFLICT:
            conflicts.setdefault(change.owner, f"{change.rel}: {change.detail}")

    items = []
    if check_writable:
        items.append(ItemResult("target writable", True, True, True,
                                PASS if writable else FAIL,
                                "" if writable else f"cannot write to {target}"))
    items.append(_verify_agents_md(target, kit_root, conflicts))
    for name in profile.skills:
        items.append(_verify_skill(target, kit_root, name, name in profile.required_skills,
                                   conflicts))
    return items


def _verify_agents_md(target: Path, kit_root: Path, conflicts: dict[str, str]) -> ItemResult:
    name = "AGENTS.md"
    if name in conflicts:
        return ItemResult(name, True, True, False, CONFLICT, conflicts[name])
    path = target / name
    if not path.is_file():
        return ItemResult(name, True, False, False, FAIL, "AGENTS.md missing")
    try:
        found = extract_block(path.read_bytes().decode("utf-8"))
    except (MarkerError, UnicodeDecodeError) as exc:
        return ItemResult(name, True, True, False, FAIL, str(exc))
    if found is None:
        return ItemResult(name, True, True, False, FAIL, "kit block missing")
    body = (kit_root / name).read_text(encoding="utf-8").strip()
    if found[2] != body:
        return ItemResult(name, True, True, True, FAIL, "kit block is outdated")
    return ItemResult(name, True, True, True, PASS)


def _verify_skill(target: Path, kit_root: Path, name: str, required: bool,
                  conflicts: dict[str, str]) -> ItemResult:
    label = f"skill:{name}"
    if label in conflicts:
        return ItemResult(label, required, True, False, CONFLICT, conflicts[label])
    skill_dir = target / ".agents" / "skills" / name
    if not skill_dir.is_dir():
        return ItemResult(label, required, False, False, FAIL, "not installed")
    errors = validate_skill(skill_dir)
    if errors:
        return ItemResult(label, required, True, True, FAIL, "; ".join(errors))
    for rel, data in iter_skill_files(kit_root, name):
        path = target / rel
        if not path.is_file() or path.read_bytes() != data:
            return ItemResult(label, required, True, True, FAIL,
                              f"files differ from the kit copy ({rel})")
    return ItemResult(label, required, True, True, PASS)
```

`kit/report.py`:
```python
"""Turn item results into READY/PARTIAL/BLOCKED, next actions and the printed report."""

from __future__ import annotations

from pathlib import Path

from .cli import Options
from .model import (
    CONFLICT,
    EXIT_BLOCKED,
    EXIT_PARTIAL,
    EXIT_READY,
    FAIL,
    PASS,
    ItemResult,
)
from .preflight import EnvReport

BAD = (FAIL, CONFLICT)


def overall_status(items: list[ItemResult], shell_fallback: bool = False) -> tuple[str, int]:
    if any(i.required and i.verified in BAD for i in items):
        return "BLOCKED", EXIT_BLOCKED
    if shell_fallback or any(i.verified in BAD for i in items):
        return "PARTIAL", EXIT_PARTIAL
    return "READY", EXIT_READY


def next_actions(items: list[ItemResult], target: Path, status: str) -> list[str]:
    actions = []
    for i in items:
        if i.verified == CONFLICT:
            actions.append(f"Resolve conflict in {i.name}: {i.detail}. "
                           "Compare with the kit copy, then re-run.")
        elif i.verified == FAIL:
            actions.append(f"Fix {i.name}: {i.detail}. Then re-run.")
    if status != "BLOCKED":
        actions.append(f"Open Codex in {target} and run /skills to confirm the kit skills load.")
    return actions[:3]


def render(env: EnvReport, opts: Options, items: list[ItemResult], status: str,
           actions: list[str]) -> str:
    skills = [i for i in items if i.name.startswith("skill:")]
    verified = sum(1 for i in skills if i.verified == PASS)
    agents = next((i for i in items if i.name == "AGENTS.md"), None)
    if agents is None:
        agents_label = "SKIPPED"
    else:
        agents_label = {PASS: "INSTALLED", CONFLICT: "CONFLICT"}.get(agents.verified, "FAILED")
    tools = ", ".join(f"{name} {'OK' if info.ok else 'missing'}"
                      for name, info in env.tools.items())
    mcp = "disabled (--no-mcp)" if opts.no_mcp else f"none in profile '{opts.profile}'"
    network = "not used (--offline)" if opts.offline else "not used"

    lines = [
        f"Environment:  {env.os} {env.arch}, shell={env.shell}, python {env.python}",
        f"Tools:        {tools}",
        f"Target:       {opts.target}",
        f"Profile:      {opts.profile}",
        f"AGENTS.md:    {agents_label}",
        f"Skills:       {len(skills)} expected / {verified} verified",
        "Codex load:   UNVERIFIED (open Codex and run /skills)",
        f"MCP:          {mcp}",
        f"Network:      {network}",
    ]
    shown = items if opts.verbose else [i for i in items if i.verified in BAD]
    if shown:
        lines.append("Items:")
        for i in shown:
            kind = "required" if i.required else "optional"
            detail = f"  ({i.detail})" if i.detail else ""
            lines.append(f"  {i.verified:<10} {kind} {i.name}{detail}")
    lines.append(f"Status:       {status}")
    lines.append("Next action:")
    lines.extend(f"  - {a}" for a in actions)
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add kit/register.py kit/verify.py kit/report.py tests/test_register.py tests/test_verify.py tests/test_report.py
git commit -m "feat: apply changes atomically, verify items and render status report"
```

---

### Task 9: Orchestration, logging and end-to-end tests

**Files:**
- Create: `kit/logs.py`, `kit/app.py`, `kit/__main__.py`, `run_kit.py`
- Create: `tests/test_registration.py`, `tests/test_idempotency.py`, `tests/test_failure_recovery.py`, `tests/test_security.py`
- Modify: `tests/conftest.py` (add `run_kit` fixture)

**Interfaces:**
- Consumes: everything above.
- Produces: `kit.logs.mask(text: str) -> str`; `write_log(target: Path, text: str, stamp: str) -> Path` (`.kit/logs/<stamp>.log`).
- Produces: `kit.app.KIT_ROOT`; `run(argv: list[str], cwd: Path | None = None, kit_root: Path = KIT_ROOT, out: TextIO | None = None) -> int`.
- Produces: conftest fixture `run_kit(*argv, cwd=None) -> tuple[int, str]` (runs `kit.app.run` in the `workspace` by default and returns exit code and stdout text).

- [ ] **Step 1: Add the `run_kit` fixture**

Append to `tests/conftest.py` (add `import io` and `from kit.app import run` to the imports):
```python
@pytest.fixture
def run_kit(workspace):
    def _run(*argv: str, cwd: Path | None = None) -> tuple[int, str]:
        out = io.StringIO()
        code = run(list(argv), cwd=cwd or workspace, out=out)
        return code, out.getvalue()

    return _run
```

- [ ] **Step 2: Write the failing end-to-end tests**

`tests/test_registration.py`:
```python
from kit.agentsmd import BEGIN


def test_first_run_is_ready(run_kit, workspace):
    code, out = run_kit()
    assert code == 0, out
    assert "Status:       READY" in out
    assert (workspace / "AGENTS.md").read_text(encoding="utf-8").startswith(BEGIN)
    assert len(list((workspace / ".agents" / "skills").iterdir())) == 6


def test_existing_agents_md_is_preserved_and_backed_up(run_kit, workspace):
    original = b"# Team rules\r\nDo not touch.\r\n"
    (workspace / "AGENTS.md").write_bytes(original)
    code, out = run_kit()
    assert code == 0, out
    data = (workspace / "AGENTS.md").read_bytes()
    assert data.startswith(original) and BEGIN.encode() in data
    backups = list((workspace / ".kit" / "backups").rglob("AGENTS.md"))
    assert [b.read_bytes() for b in backups] == [original]


def test_user_edited_required_skill_blocks_and_is_kept(run_kit, workspace):
    run_kit()
    skill = workspace / ".agents/skills/task-router/SKILL.md"
    edited = skill.read_bytes() + b"\nmy note\n"
    skill.write_bytes(edited)
    code, out = run_kit()
    assert code == 2, out
    assert "Status:       BLOCKED" in out and "skill:task-router" in out
    assert skill.read_bytes() == edited


def test_user_edited_optional_skill_is_partial(run_kit, workspace):
    run_kit()
    skill = workspace / ".agents/skills/benchmark/SKILL.md"
    skill.write_bytes(skill.read_bytes() + b"\nmy note\n")
    code, out = run_kit()
    assert code == 1, out
    assert "Status:       PARTIAL" in out


def test_unknown_profile_exits_64(run_kit):
    assert run_kit("--profile", "gpu")[0] == 64


def test_missing_target_exits_65(run_kit, tmp_path):
    assert run_kit("--target", str(tmp_path / "missing"))[0] == 65


def test_no_mcp_flag_is_reported(run_kit):
    code, out = run_kit("--no-mcp")
    assert code == 0 and "MCP:          disabled (--no-mcp)" in out
```

`tests/test_idempotency.py`:
```python
from conftest import tree_digest


def test_second_run_changes_nothing(run_kit, workspace):
    assert run_kit()[0] == 0
    first = tree_digest(workspace)
    code, out = run_kit()
    assert code == 0, out
    assert tree_digest(workspace) == first


def test_dry_run_writes_nothing(run_kit, workspace):
    code, out = run_kit("--dry-run")
    assert code == 0, out
    assert "CREATE" in out and "DRY RUN: nothing was written." in out
    assert list(workspace.iterdir()) == []


def test_dry_run_after_install_plans_nothing(run_kit):
    run_kit()
    code, out = run_kit("--dry-run")
    assert code == 0
    assert "0 create, 0 update, 0 append, 0 conflict" in out


def test_lost_state_is_adopted(run_kit, workspace):
    run_kit()
    state = workspace / ".kit" / "state.json"
    before = state.read_bytes()
    state.unlink()
    code, out = run_kit()
    assert code == 0, out
    assert state.read_bytes() == before


def test_verify_only_writes_only_logs(run_kit, workspace):
    code, out = run_kit("--verify-only")
    assert code == 2, out
    written = [p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()]
    assert written and all(rel.startswith(".kit/logs/") for rel in written)
```

`tests/test_failure_recovery.py`:
```python
import os


def test_interrupted_run_recovers_on_rerun(run_kit, workspace, monkeypatch):
    real_replace = os.replace
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("simulated disk error")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    code, out = run_kit()
    assert code == 2, out
    assert "error: write failed: simulated disk error" in out

    monkeypatch.setattr(os, "replace", real_replace)
    code, out = run_kit()
    assert code == 0, out
    assert not list(workspace.rglob("*.kit-tmp"))
```

`tests/test_security.py`:
```python
import re

from kit.logs import mask

FORBIDDEN = [
    re.compile(r"git\s+push"),
    re.compile(r"curl[^\n|]*\|\s*(ba)?sh"),
    re.compile(r"\|\s*iex\b", re.IGNORECASE),
    re.compile(r"Invoke-Expression", re.IGNORECASE),
]
NETWORK_IMPORT = re.compile(r"^\s*(import|from)\s+(socket|urllib|http)\b", re.MULTILINE)
CODE_GLOBS = ["kit/*.py", "run_kit.py", "bootstrap.sh", "bootstrap.ps1"]


def test_mask_hides_tokens():
    text = ("sk-abcdefghijklmnopqrstuv ghp_ABCDEFGHIJKLMNOPQRSTUVWX12 "
            "API_KEY=hunter2 password: opensesame")
    masked = mask(text)
    for secret in ("sk-abcdefghijklmnopqrstuv", "ghp_ABCDEFGHIJKLMNOPQRSTUVWX12",
                   "hunter2", "opensesame"):
        assert secret not in masked
    assert "API_KEY=***" in masked


def test_log_never_contains_environment_values(run_kit, workspace, monkeypatch):
    monkeypatch.setenv("KIT_TEST_SECRET", "ghp_" + "Z" * 30)
    run_kit()
    logs = list((workspace / ".kit" / "logs").glob("*.log"))
    assert logs
    for log in logs:
        assert "ZZZZZZZZZZ" not in log.read_text(encoding="utf-8")


def test_kit_code_has_no_push_or_pipe_to_shell(kit_root):
    files = [p for pattern in CODE_GLOBS for p in kit_root.glob(pattern)]
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            assert not pattern.search(text), f"{path.name}: {pattern.pattern}"


def test_kit_core_imports_no_network_modules(kit_root):
    for path in kit_root.glob("kit/*.py"):
        assert not NETWORK_IMPORT.search(path.read_text(encoding="utf-8")), path.name


def test_no_writes_outside_target(run_kit, workspace, tmp_path):
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    run_kit()
    assert list(sibling.iterdir()) == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest -q`
Expected: FAIL at collection — `ModuleNotFoundError: No module named 'kit.app'`.

- [ ] **Step 4: Implement**

`kit/logs.py`:
```python
"""Local-only run logs with secrets masked. Environment variable values are never logged."""

from __future__ import annotations

import re
from pathlib import Path

from .fsops import safe_path

_PATTERNS = [
    (re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[=:]\s*\S+"), r"\1=***"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "***"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "***"),
]


def mask(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def write_log(target: Path, text: str, stamp: str) -> Path:
    path = safe_path(target, f".kit/logs/{stamp}.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(mask(text).encode("utf-8"))
    return path
```

`kit/app.py`:
```python
"""Orchestration: preflight -> plan -> apply -> verify -> report."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from .cli import Options, parse_args
from .fsops import State, timestamp
from .logs import write_log
from .model import EXIT_READY, EXIT_TARGET, EXIT_USAGE, TargetError, UsageError
from .plan import FileChange, format_plan, plan_changes
from .preflight import EnvReport, run_preflight
from .profiles import available_profiles, load_profile
from .register import apply_changes
from .report import next_actions, overall_status, render
from .verify import verify_target

KIT_ROOT = Path(__file__).resolve().parent.parent


def run(argv: list[str], cwd: Path | None = None, kit_root: Path = KIT_ROOT,
        out: TextIO | None = None) -> int:
    out = out or sys.stdout
    cwd = cwd or Path.cwd()
    try:
        opts = parse_args(argv, cwd, available_profiles(kit_root))
        profile = load_profile(kit_root, opts.profile)
    except UsageError as exc:
        print(f"error: {exc}\nRun with --help for usage.", file=sys.stderr)
        return EXIT_USAGE
    except TargetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TARGET

    env = run_preflight(opts.target)
    state = State.load(opts.target)
    changes = plan_changes(opts.target, kit_root, profile, state)

    if opts.dry_run:
        out.write(_dry_run_text(opts, env, changes))
        return EXIT_READY

    stamp = timestamp()
    lines = []
    if not opts.verify_only and env.target_writable:
        try:
            apply_changes(opts.target, changes, state, stamp, opts.profile)
        except OSError as exc:
            lines.append(f"error: write failed: {exc}")

    items = verify_target(opts.target, kit_root, profile, changes,
                          check_writable=not opts.verify_only, writable=env.target_writable)
    status, code = overall_status(items)
    lines.append(render(env, opts, items, status, next_actions(items, opts.target, status)))
    text = "\n".join(lines)
    out.write(text)
    if env.target_writable:
        try:
            write_log(opts.target, text, stamp)
        except OSError:
            pass
    return code


def _dry_run_text(opts: Options, env: EnvReport, changes: list[FileChange]) -> str:
    return "\n".join([
        f"Environment:  {env.os} {env.arch}, shell={env.shell}, python {env.python}",
        f"Target:       {opts.target}",
        f"Profile:      {opts.profile}",
        "Network:      none (this profile installs no tools)",
        "Planned changes:",
        format_plan(changes, opts.verbose),
        "DRY RUN: nothing was written.",
        "",
    ])
```

`kit/__main__.py`:
```python
import sys

from .app import run

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
```

`run_kit.py`:
```python
"""Entry used by bootstrap.sh/.ps1 (`python -I run_kit.py ...`); avoids PYTHONPATH quirks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit.app import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: all passed.

- [ ] **Step 6: Smoke test the real entry**

Run (PowerShell): `$ws = New-Item -ItemType Directory -Force "$env:TEMP\kit-smoke"; uv run python -I run_kit.py --target $ws; "exit=$LASTEXITCODE"`
Expected: report ends with `Status:       READY`, `exit=0`. Run it a second time: same output, `exit=0`. Then `Remove-Item -Recurse -Force $ws`.

- [ ] **Step 7: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add kit/logs.py kit/app.py kit/__main__.py run_kit.py tests
git commit -m "feat: orchestrate bootstrap run with masked local logs and end-to-end tests"
```

---

### Task 10: `bootstrap.sh`

**Files:**
- Create: `bootstrap.sh`, `tests/test_entrypoints.py`

**Interfaces:**
- Consumes: `run_kit.py`; env var `KIT_PYTHON` (if set, it is the only interpreter tried; an unusable value forces shell-only mode); sets `KIT_SHELL=bash` for the Python core.
- Produces: shell-only output lines `  CREATE    <path>`, `  SKIP      <path>`, `  CONFLICT  <path>`; `Status:       PARTIAL` (exit 1), `Status:       BLOCKED` (exit 2, AGENTS.md conflict), dry-run exit 0.

- [ ] **Step 1: Write the failing tests**

`tests/test_entrypoints.py`:
```python
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kit.agentsmd import BEGIN

KIT_ROOT = Path(__file__).resolve().parent.parent
NO_PYTHON = "kit-no-such-python"


def _find_bash():
    if os.environ.get("KIT_TEST_BASH"):
        return os.environ["KIT_TEST_BASH"]
    if os.name == "nt":
        # C:\Windows\System32\bash.exe is WSL, which cannot see this Python; use Git Bash.
        git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git/bin/bash.exe"
        return str(git_bash) if git_bash.is_file() else None
    return shutil.which("bash")


def _find_powershell():
    return shutil.which("powershell") or shutil.which("pwsh")


BASH = _find_bash()
POWERSHELL = _find_powershell()
SHELLS = ["bash", "powershell"]


def _command(kind):
    if kind == "bash":
        if not BASH:
            pytest.skip("bash not found")
        return [BASH, (KIT_ROOT / "bootstrap.sh").as_posix()]
    if not POWERSHELL:
        pytest.skip("PowerShell not found")
    return [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(KIT_ROOT / "bootstrap.ps1")]


def _path(kind, path):
    return path.as_posix() if kind == "bash" else str(path)


def _python(kind):
    return Path(sys.executable).as_posix() if kind == "bash" else sys.executable


def _run(kind, *args, cwd, python):
    env = dict(os.environ, KIT_PYTHON=python)
    return subprocess.run(_command(kind) + list(args), cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=180)


@pytest.mark.parametrize("kind", SHELLS)
def test_help_exits_zero(kind, workspace):
    proc = _run(kind, "--help", cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 0, proc.stderr
    assert "Usage" in proc.stdout and "Exit codes" in proc.stdout


@pytest.mark.parametrize("kind", SHELLS)
@pytest.mark.parametrize("with_python", [True, False])
def test_bad_argument_exits_64(kind, with_python, workspace):
    python = _python(kind) if with_python else NO_PYTHON
    assert _run(kind, "--bogus", cwd=workspace, python=python).returncode == 64


@pytest.mark.parametrize("kind", SHELLS)
@pytest.mark.parametrize("with_python", [True, False])
def test_missing_target_exits_65(kind, with_python, workspace):
    python = _python(kind) if with_python else NO_PYTHON
    missing = _path(kind, workspace / "missing")
    assert _run(kind, "--target", missing, cwd=workspace, python=python).returncode == 65


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_installs_then_skips(kind, workspace):
    first = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert first.returncode == 1, first.stdout + first.stderr
    assert "shell-only" in first.stdout and "Status:       PARTIAL" in first.stdout
    assert (workspace / "AGENTS.md").read_text(encoding="utf-8").startswith(BEGIN)
    assert len(list((workspace / ".agents" / "skills").iterdir())) == 6
    second = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert second.returncode == 1
    assert "SKIP" in second.stdout and "CONFLICT" not in second.stdout


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_conflicts_on_foreign_agents_md(kind, workspace):
    (workspace / "AGENTS.md").write_bytes(b"mine\n")
    proc = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 2, proc.stdout
    assert "Status:       BLOCKED" in proc.stdout
    assert (workspace / "AGENTS.md").read_bytes() == b"mine\n"


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_dry_run_writes_nothing(kind, workspace):
    proc = _run(kind, "--dry-run", cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 0, proc.stdout
    assert "DRY RUN" in proc.stdout
    assert list(workspace.iterdir()) == []


@pytest.mark.parametrize("kind", SHELLS)
def test_delegates_to_python(kind, workspace):
    proc = _run(kind, "--target", _path(kind, workspace), cwd=workspace, python=_python(kind))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Status:       READY" in proc.stdout
    assert f"shell={kind}" in proc.stdout


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_output_upgrades_cleanly_with_python(kind, workspace):
    _run(kind, cwd=workspace, python=NO_PYTHON)
    proc = _run(kind, cwd=workspace, python=_python(kind))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Status:       READY" in proc.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_entrypoints.py -k bash -q`
Expected: FAIL — bash reports `No such file or directory` for `bootstrap.sh` (non-zero exit codes).

- [ ] **Step 3: Implement**

`bootstrap.sh`:
```bash
#!/usr/bin/env bash
# Entry point for bash. Hands off to the Python core when Python 3.9+ exists;
# otherwise copies AGENTS.md and the skills into the target (shell-only mode).
set -u

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BEGIN_MARK='<!-- hackathon-kit:begin -->'
END_MARK='<!-- hackathon-kit:end -->'

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [--profile core|python|data|web|full] [--target DIR]
                    [--dry-run] [--offline] [--verify-only] [--no-mcp] [--verbose]

Installs AGENTS.md and the Codex skills into the target workspace
(default: current directory). Python 3.9+ enables verification, tools and MCP;
without Python only AGENTS.md and the skills are copied.

Exit codes:
  0   READY (or dry-run completed)
  1   PARTIAL - required items OK, optional items failed or unsupported
  2   BLOCKED - a required item failed or needs your decision
  64  invalid arguments
  65  target workspace missing or not a directory
EOF
}

python_ok() {
  "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1
}

find_python() {
  if [ -n "${KIT_PYTHON+set}" ]; then
    python_ok "$KIT_PYTHON" && printf '%s\n' "$KIT_PYTHON"
    return
  fi
  for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1 && python_ok "$cand"; then
      printf '%s\n' "$cand"
      return 0
    fi
  done
  return 1
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
  esac
done

if PY="$(find_python)"; then
  export KIT_SHELL=bash
  exec "$PY" -I "$KIT_ROOT/run_kit.py" "$@"
fi

# ---- shell-only mode -------------------------------------------------------
TARGET="$PWD"
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)
      [ $# -ge 2 ] || { echo "error: --profile needs a value" >&2; exit 64; }
      case "$2" in
        core|python|data|web|full) ;;
        *) echo "error: unknown profile: $2" >&2; exit 64 ;;
      esac
      shift 2 ;;
    --target)
      [ $# -ge 2 ] || { echo "error: --target needs a value" >&2; exit 64; }
      TARGET="$2"
      shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --offline|--verify-only|--no-mcp|--verbose) shift ;;
    *)
      echo "error: unknown argument: $1" >&2
      echo "Run with --help for usage." >&2
      exit 64 ;;
  esac
done

if [ ! -d "$TARGET" ]; then
  echo "error: target is not an existing directory: $TARGET" >&2
  exit 65
fi
TARGET="$(cd "$TARGET" && pwd)"
CONFLICT=0

note() { printf '  %-9s %s\n' "$1" "$2"; }

echo "Python 3.9+ not found: shell-only mode (copies AGENTS.md and skills; installs nothing)."

if [ -e "$TARGET/AGENTS.md" ]; then
  if grep -qF -- "$BEGIN_MARK" "$TARGET/AGENTS.md"; then
    note SKIP "AGENTS.md (kit block present)"
  else
    note CONFLICT "AGENTS.md (exists; merging needs Python - add the kit block by hand)"
    CONFLICT=1
  fi
elif [ "$DRY_RUN" -eq 1 ]; then
  note CREATE AGENTS.md
else
  { printf '%s\n' "$BEGIN_MARK"; cat "$KIT_ROOT/AGENTS.md"; printf '%s\n' "$END_MARK"; } \
    > "$TARGET/AGENTS.md"
  note CREATE AGENTS.md
fi

for src in "$KIT_ROOT"/.agents/skills/*/; do
  name="$(basename "$src")"
  dest="$TARGET/.agents/skills/$name"
  if [ -e "$dest" ]; then
    note SKIP ".agents/skills/$name (exists)"
  elif [ "$DRY_RUN" -eq 1 ]; then
    note CREATE ".agents/skills/$name"
  else
    if ! { mkdir -p "$TARGET/.agents/skills" && cp -R "${src%/}" "$dest"; }; then
      echo "error: could not copy skill $name" >&2
      exit 2
    fi
    note CREATE ".agents/skills/$name"
  fi
done

echo "Target:       $TARGET"
echo "Mode:         shell-only (no Python 3.9+)"
echo "Codex load:   UNVERIFIED (open Codex and run /skills)"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN: nothing was written."
  exit 0
fi
if [ "$CONFLICT" -eq 1 ]; then
  echo "Status:       BLOCKED"
  echo "Next action:"
  echo "  - Add the kit block from $KIT_ROOT/AGENTS.md to $TARGET/AGENTS.md by hand, or install Python 3.9+ and re-run."
  exit 2
fi
echo "Status:       PARTIAL"
echo "Next action:"
echo "  - Install Python 3.9+ and re-run to verify files and enable tools/MCP."
echo "  - Open Codex in $TARGET and run /skills to confirm the kit skills load."
exit 1
```

Mark it executable in git: `git add bootstrap.sh && git update-index --chmod=+x bootstrap.sh`

- [ ] **Step 4: Run tests and shellcheck**

Run: `uv run pytest tests/test_entrypoints.py -k bash -q`
Expected: all bash cases passed.
Run: `shellcheck bootstrap.sh`
Expected: no output (exit 0). Fix any warning it reports before committing.

- [ ] **Step 5: Commit**

```bash
git add bootstrap.sh tests/test_entrypoints.py
git update-index --chmod=+x bootstrap.sh
git commit -m "feat: add bash entry point with shell-only fallback"
```

---

### Task 11: `bootstrap.ps1`

**Files:**
- Create: `bootstrap.ps1`

**Interfaces:**
- Same contract as Task 10 (options, output lines, exit codes); sets `KIT_SHELL=powershell`. Tests are the `powershell` cases already in `tests/test_entrypoints.py`.

- [ ] **Step 1: Confirm the PowerShell tests fail**

Run: `uv run pytest tests/test_entrypoints.py -k powershell -q`
Expected: FAIL — `-File` reports the script does not exist (non-zero exit codes).

- [ ] **Step 2: Implement (ASCII only)**

`bootstrap.ps1`:
```powershell
# Entry point for Windows PowerShell 5.1+. Hands off to the Python core when
# Python 3.9+ exists; otherwise copies AGENTS.md and the skills (shell-only mode).
# Keep this file ASCII-only: Windows PowerShell 5.1 reads BOM-less files as ANSI.

$KitRoot = $PSScriptRoot
$BeginMark = '<!-- hackathon-kit:begin -->'
$EndMark = '<!-- hackathon-kit:end -->'
$ProfileNames = @('core', 'python', 'data', 'web', 'full')

$Usage = @'
Usage: bootstrap.ps1 [--profile core|python|data|web|full] [--target DIR]
                     [--dry-run] [--offline] [--verify-only] [--no-mcp] [--verbose]

Installs AGENTS.md and the Codex skills into the target workspace
(default: current directory). Python 3.9+ enables verification, tools and MCP;
without Python only AGENTS.md and the skills are copied.

Exit codes:
  0   READY (or dry-run completed)
  1   PARTIAL - required items OK, optional items failed or unsupported
  2   BLOCKED - a required item failed or needs your decision
  64  invalid arguments
  65  target workspace missing or not a directory
'@

function Test-Python([string]$Exe, [string[]]$Prefix) {
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { return $false }
    try {
        & $Exe @Prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Write-Note([string]$Kind, [string]$Path) {
    Write-Output ('  {0,-9} {1}' -f $Kind, $Path)
}

function Write-Err([string]$Message) {
    [Console]::Error.WriteLine($Message)
}

foreach ($arg in $args) {
    if ($arg -eq '--help' -or $arg -eq '-h') { Write-Output $Usage; exit 0 }
}

$Python = $null
if (Test-Path Env:KIT_PYTHON) {
    if (Test-Python $env:KIT_PYTHON @()) { $Python = @($env:KIT_PYTHON) }
} else {
    foreach ($cand in @('python3', 'python', 'py -3')) {
        $parts = @($cand -split ' ')
        $prefix = @($parts | Select-Object -Skip 1)
        if (Test-Python $parts[0] $prefix) { $Python = $parts; break }
    }
}

if ($null -ne $Python) {
    $env:KIT_SHELL = 'powershell'
    $prefix = @($Python | Select-Object -Skip 1)
    & $Python[0] @prefix -I (Join-Path $KitRoot 'run_kit.py') @args
    exit $LASTEXITCODE
}

# ---- shell-only mode -------------------------------------------------------
$Target = (Get-Location).Path
$DryRun = $false
$i = 0
while ($i -lt $args.Count) {
    $a = [string]$args[$i]
    if ($a -eq '--profile') {
        if ($i + 1 -ge $args.Count) { Write-Err 'error: --profile needs a value'; exit 64 }
        if ($ProfileNames -notcontains [string]$args[$i + 1]) {
            Write-Err "error: unknown profile: $($args[$i + 1])"; exit 64
        }
        $i += 2
    } elseif ($a -eq '--target') {
        if ($i + 1 -ge $args.Count) { Write-Err 'error: --target needs a value'; exit 64 }
        $Target = [string]$args[$i + 1]
        $i += 2
    } elseif ($a -eq '--dry-run') {
        $DryRun = $true
        $i += 1
    } elseif (@('--offline', '--verify-only', '--no-mcp', '--verbose') -contains $a) {
        $i += 1
    } else {
        Write-Err "error: unknown argument: $a"
        Write-Err 'Run with --help for usage.'
        exit 64
    }
}

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    Write-Err "error: target is not an existing directory: $Target"
    exit 65
}
$Target = (Resolve-Path -LiteralPath $Target).ProviderPath
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
$Conflict = $false

Write-Output 'Python 3.9+ not found: shell-only mode (copies AGENTS.md and skills; installs nothing).'

$AgentsPath = Join-Path $Target 'AGENTS.md'
if (Test-Path -LiteralPath $AgentsPath) {
    $existing = [System.IO.File]::ReadAllText($AgentsPath)
    if ($existing.Contains($BeginMark)) {
        Write-Note 'SKIP' 'AGENTS.md (kit block present)'
    } else {
        Write-Note 'CONFLICT' 'AGENTS.md (exists; merging needs Python - add the kit block by hand)'
        $Conflict = $true
    }
} elseif ($DryRun) {
    Write-Note 'CREATE' 'AGENTS.md'
} else {
    $body = [System.IO.File]::ReadAllText((Join-Path $KitRoot 'AGENTS.md')).Replace("`r`n", "`n").Trim()
    [System.IO.File]::WriteAllText($AgentsPath, "$BeginMark`n$body`n$EndMark`n", $Utf8NoBom)
    Write-Note 'CREATE' 'AGENTS.md'
}

$SkillsSrc = Join-Path $KitRoot '.agents\skills'
$SkillsDst = Join-Path $Target '.agents\skills'
foreach ($dir in Get-ChildItem -LiteralPath $SkillsSrc -Directory) {
    $dest = Join-Path $SkillsDst $dir.Name
    $rel = ".agents/skills/$($dir.Name)"
    if (Test-Path -LiteralPath $dest) {
        Write-Note 'SKIP' "$rel (exists)"
    } elseif ($DryRun) {
        Write-Note 'CREATE' $rel
    } else {
        try {
            New-Item -ItemType Directory -Force -Path $SkillsDst -ErrorAction Stop | Out-Null
            Copy-Item -LiteralPath $dir.FullName -Destination $dest -Recurse -ErrorAction Stop
        } catch {
            Write-Err "error: could not copy skill $($dir.Name): $_"
            exit 2
        }
        Write-Note 'CREATE' $rel
    }
}

Write-Output "Target:       $Target"
Write-Output 'Mode:         shell-only (no Python 3.9+)'
Write-Output 'Codex load:   UNVERIFIED (open Codex and run /skills)'
if ($DryRun) {
    Write-Output 'DRY RUN: nothing was written.'
    exit 0
}
if ($Conflict) {
    Write-Output 'Status:       BLOCKED'
    Write-Output 'Next action:'
    Write-Output "  - Add the kit block from $KitRoot\AGENTS.md to $AgentsPath by hand, or install Python 3.9+ and re-run."
    exit 2
}
Write-Output 'Status:       PARTIAL'
Write-Output 'Next action:'
Write-Output '  - Install Python 3.9+ and re-run to verify files and enable tools/MCP.'
Write-Output "  - Open Codex in $Target and run /skills to confirm the kit skills load."
exit 1
```

- [ ] **Step 3: Check the file is ASCII**

Run: `uv run python -c "open('bootstrap.ps1','rb').read().decode('ascii'); print('ascii ok')"`
Expected: `ascii ok`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_entrypoints.py -q`
Expected: all bash and powershell cases passed.

- [ ] **Step 5: Static analysis if available**

Run (PowerShell): `if (Get-Module -ListAvailable PSScriptAnalyzer) { Invoke-ScriptAnalyzer -Path bootstrap.ps1 } else { 'PSScriptAnalyzer not installed - not run' }`
Expected: no Error-severity findings, or the "not run" line (record which in Task 12).

- [ ] **Step 6: Commit**

```bash
git add bootstrap.ps1
git commit -m "feat: add PowerShell entry point with shell-only fallback"
```

---

### Task 12: Plan-1 docs and full verification

**Files:**
- Create: `README.md`, `docs/ASSUMPTIONS.md`, `docs/TEST_REPORT.md`

**Interfaces:**
- Consumes: the whole repo. No code changes unless verification finds a bug (then fix it in the task that owns the file, with a failing test first).

- [ ] **Step 1: Write `README.md`**

````markdown
# hackathon-agent-kit

> **Claude Code 사전 개발 전용 / 시험 중 사용 불가.** 이 저장소는 시험 전에 Claude Code로 개발했다. 시험 중에는 운영 환경이 제공하는 Codex만 사용하며, 이 키트는 Codex가 읽을 `AGENTS.md`와 Skill 파일을 작업 공간에 배치할 뿐 외부 모델이나 네트워크를 호출하지 않는다.

대상 작업 공간에 Codex용 정책 파일(`AGENTS.md`)과 Skill 6개(`.agents/skills/`)를 안전하게 설치하고, 설치 결과를 READY / PARTIAL / BLOCKED로 보고한다.

## 한 줄 설치

`<USER>`와 `<REPO>`를 본인 GitHub 주소로 바꾼다. 복제와 실행은 분리돼 있다(`curl | bash` 방식 아님).

bash (Linux/macOS/Git Bash):

```bash
git clone --depth 1 https://github.com/<USER>/<REPO>.git && bash <REPO>/bootstrap.sh --target .
```

Windows PowerShell:

```powershell
git clone --depth 1 https://github.com/<USER>/<REPO>.git; if ($LASTEXITCODE -eq 0) { & .\<REPO>\bootstrap.ps1 --target . }
```

실행 정책 때문에 `.ps1`이 막히면 스크립트를 우회하지 말고 아래 "스크립트를 실행할 수 없을 때"를 따른다.

## 옵션

| 옵션 | 의미 |
|---|---|
| `--profile core` | 기본값. AGENTS.md와 Skill 6개만 설치(도구·MCP 없음). 다른 프로필은 계획 2에서 추가 |
| `--target <dir>` | 설치 대상 작업 공간(기본: 현재 디렉터리) |
| `--dry-run` | 아무것도 쓰지 않고 계획만 출력 |
| `--verify-only` | 설치 없이 현재 상태만 검사(로그만 기록) |
| `--offline` | 네트워크를 쓰지 않음(core는 원래 쓰지 않음) |
| `--no-mcp` | MCP를 건너뜀 |
| `--verbose` | 파일·항목별 상세 출력 |
| `--help` | 도움말 |

## 종료 코드

| 코드 | 상태 | 의미 |
|---|---|---|
| 0 | READY | 필수 항목 모두 검증(또는 dry-run 완료) |
| 1 | PARTIAL | 필수 항목은 정상, 선택 항목 일부 실패 또는 Python 없이 셸 모드로 실행 |
| 2 | BLOCKED | 필수 항목 실패 또는 사용자 판단이 필요한 충돌 |
| 64 | - | 잘못된 인수 |
| 65 | - | 대상 디렉터리가 없거나 디렉터리가 아님 |

## 예상 출력

```text
Environment:  Windows 11 AMD64, shell=powershell, python 3.12.10
Tools:        git OK, uv OK, node OK, npx OK, codex OK, python OK
Target:       D:\work\task
Profile:      core
AGENTS.md:    INSTALLED
Skills:       6 expected / 6 verified
Codex load:   UNVERIFIED (open Codex and run /skills)
MCP:          none in profile 'core'
Network:      not used
Status:       READY
Next action:
  - Open Codex in D:\work\task and run /skills to confirm the kit skills load.
```

`Codex load: UNVERIFIED`는 정상이다. Codex가 Skill을 실제로 읽었는지는 Codex 안에서 `/skills`로만 확인할 수 있다.

## 안전 장치

- 기존 `AGENTS.md`는 덮어쓰지 않는다. 키트 내용은 `<!-- hackathon-kit:begin -->` … `<!-- hackathon-kit:end -->` 구간에만 쓰고, 수정 전 원본을 `.kit/backups/<시각>/`에 남긴다.
- 사용자가 고친 파일은 `CONFLICT`로 보고하고 건드리지 않는다.
- 같은 명령을 다시 실행해도 결과가 같다(멱등). 중간에 실패해도 다시 실행하면 이어서 맞춰진다.
- 대상 디렉터리 밖에는 쓰지 않으며 `~/.codex` 같은 전역 설정은 건드리지 않는다.
- 로그는 대상의 `.kit/logs/`에만 남고 토큰 형태 문자열은 가려진다.

## 스크립트를 실행할 수 없을 때

키트 폴더의 `AGENTS.md` 내용과 `.agents/` 폴더를 작업 공간 루트에 그대로 복사하면 된다. 그다음 Codex에서 `/skills`로 확인한다.

## 개발

```bash
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
shellcheck bootstrap.sh
```

## 공개 전 점검

- [ ] `LICENSE`(MIT) 저자·연도 확인
- [ ] README의 `<USER>/<REPO>`를 실제 주소로 교체
- [ ] 저장소에 토큰·개인 경로·시험 관련 비공개 자료가 없는지 확인
- [ ] `docs/TEST_REPORT.md`가 최신인지 확인
````

- [ ] **Step 2: Write `docs/ASSUMPTIONS.md`**

```markdown
# 가정과 미확인 사항

`UNVERIFIED`는 사전 체험이나 운영 측 확인 전까지 사실로 취급하지 않는다는 뜻이다.

## 시험 환경 (모두 UNVERIFIED)

| 항목 | 상태 | 확인 방법 | 안 될 때 |
|---|---|---|---|
| bash 또는 PowerShell 실행 가능 | UNVERIFIED | 사전 체험에서 터미널 열기 | 파일 수동 복사 |
| git 사용 가능 / 공개 GitHub 접근 | UNVERIFIED | `git clone` 시도 | 키트를 받을 수 없으면 키트 없이 진행 |
| Python 3.9+ 존재 | UNVERIFIED | `python --version` | 셸 모드(PARTIAL)로 진행 |
| 스크립트 자동 설치 허용 | UNVERIFIED | 공지·감독관 확인 | 실행하지 않고 수동 복사 |
| Codex가 `.agents/skills`를 탐색 | UNVERIFIED | Codex에서 `/skills` | `AGENTS.md`만으로 진행 |
| 설치한 파일이 세션 동안 유지 | UNVERIFIED | 재접속 후 파일 확인 | 다시 실행(멱등) |

## 로컬에서 확인한 사실 (2026-10-28, codex-cli 0.164.0)

- Skill 탐색 경로: `$CWD/.agents/skills` ~ 저장소 루트의 `.agents/skills`, `$HOME/.agents/skills`.
- `agents/openai.yaml`의 `policy.allow_implicit_invocation: false`로 명시 호출 전용 Skill을 만들 수 있다.
- `codex debug prompt-input` 출력에는 Skill 목록이 나타나지 않는다. Skill 로드는 비대화형으로 검증할 수 없어 보고서에 `Codex load: UNVERIFIED`로 표시한다.
- 프로젝트 `.codex/config.toml`은 신뢰된 프로젝트에서만 로드된다(계획 2의 MCP에 해당).

## 설계상 가정

- 대상 작업 공간은 Codex를 실행할 디렉터리(또는 그 상위 저장소 루트)다.
- 텍스트 파일은 UTF-8이다. UTF-8이 아닌 기존 `AGENTS.md`는 CONFLICT로 남긴다.
```

- [ ] **Step 3: Run the full verification and capture output**

Run each, keeping the full output:
```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
shellcheck bootstrap.sh
```
Run (PowerShell): `if (Get-Module -ListAvailable PSScriptAnalyzer) { Invoke-ScriptAnalyzer -Path bootstrap.ps1 } else { 'PSScriptAnalyzer not installed - not run' }`

Expected: pytest all passed (symlink test may be skipped on Windows), ruff clean, shellcheck clean.

- [ ] **Step 4: Reproduce the one-liner on a clean local clone**

Run (PowerShell):
```powershell
$sandbox = New-Item -ItemType Directory -Force "$env:TEMP\kit-oneliner"
Push-Location $sandbox
git clone --depth 1 --branch feat/bootstrap-kit file:///D:/aaa/aaa kit; if ($LASTEXITCODE -eq 0) { & .\kit\bootstrap.ps1 --target . }
"exit=$LASTEXITCODE"
& .\kit\bootstrap.ps1 --target .
"exit=$LASTEXITCODE"
Pop-Location
```
Expected: both runs end with `Status:       READY` and `exit=0`. Repeat with Git Bash: `cd "$TEMP/kit-oneliner" && bash kit/bootstrap.sh --target .` → `READY`, exit 0. Then remove the sandbox.

- [ ] **Step 5: Manual Codex check (user)**

Ask the user to run in the sandbox (TUI, interactive): `codex` then `/skills`. Record whether the six skills appear, and whether `implementation-review` and `benchmark` are marked explicit-only. If the user does not run it, record `UNVERIFIED`.

- [ ] **Step 6: Write `docs/TEST_REPORT.md`**

Record what actually ran, copying the real output from Steps 3–5:

```markdown
# 테스트 보고서 (계획 1)

실행일: <date of the run>, 환경: <OS, Python, codex version from the report>

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run pytest -q` | <PASS/FAIL> | <summary line, e.g. "87 passed, 1 skipped"> |
| `uv run ruff check .` | <PASS/FAIL> | <output> |
| `uv run ruff format --check .` | <PASS/FAIL> | <output> |
| `shellcheck bootstrap.sh` | <PASS/FAIL> | <output> |
| PSScriptAnalyzer | <PASS/FAIL/미실행> | <output or "not installed"> |
| one-liner (PowerShell, clean clone) | <PASS/FAIL> | <Status line, exit code, both runs> |
| one-liner (Git Bash) | <PASS/FAIL> | <Status line, exit code> |
| Codex `/skills` | <PASS/FAIL/UNVERIFIED> | <what the user saw> |

## 건너뛴 테스트와 이유
- <e.g. symlink escape test skipped: symlinks need developer mode on Windows>

## 미검증
- 시험 환경(Cofa) 전체: docs/ASSUMPTIONS.md 참고
```

Fill every `<…>` with the real values from the run; leave nothing in angle brackets.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/ASSUMPTIONS.md docs/TEST_REPORT.md
git commit -m "docs: add README, assumptions and plan-1 test report"
```

---

## Self-Review Notes

- Spec coverage (plan 1 scope): §3 architecture → Tasks 1–9; §3.1 dry-run/verify-only/no-mcp/offline → Tasks 2, 9 (offline/no-mcp only affect reporting in core; real effect arrives with tools/MCP in plan 2); §3.2 state/idempotency → Tasks 6, 7, 9; §3.3 AGENTS.md merge → Task 6; §4 skills → Tasks 4, 5; §5 status rules → Task 8; §9 entry points → Tasks 10, 11; §10 tests → every task; §12 docs (README, ASSUMPTIONS, TEST_REPORT) → Task 12.
- Deferred to plan 2 by design: §3.4 MCP registration, §6 python/data/web/full profiles, §7 MCP manifest, §8 `audit.py` (plan 1 covers the repo scan, path confinement and log masking parts), docs ARCHITECTURE/SECURITY/COMPATIBILITY/RULES_CHECKLIST/TROUBLESHOOTING, example logs.
