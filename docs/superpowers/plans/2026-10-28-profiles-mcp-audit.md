# Profiles, MCP and Audit (Plan 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Plan 1 bootstrap core with the python/data/web/full profiles, the sequential-thinking MCP server (config block, stdio handshake, Codex listing), a security audit of the target's `.codex/config.toml`, and the remaining Korean docs with example logs.

**Architecture:** Every new capability is a small `kit/` module that returns `ItemResult`s, wired into `kit/app.py` after the existing file verification. File writes still go through `plan.py` → `register.py` (the config block reuses the AGENTS.md protected-block merge with `#` markers). Tool installs and MCP processes go through two patchable functions (`tools.run_command`, `mcpcheck.handshake`) so tests never touch the network.

**Tech Stack:** Python 3.9+ standard library only (`tomllib` used when available, 3.11+), pytest, ruff; existing bash/PowerShell entry points unchanged.

## Global Constraints

- Python 3.9+ standard library only in `kit/`; no runtime dependencies. `tomllib` only via guarded import; on 3.9–3.10 TOML parse and config audit report `UNVERIFIED`.
- Exit codes unchanged: 0 READY (also dry-run), 1 PARTIAL, 2 BLOCKED, 64 usage, 65 target.
- Writes only inside the target (`AGENTS.md`, `.agents/skills/`, `.codex/config.toml`, `.kit/`). Never read-modify `~/.codex` or `~/.agents`.
- Config block markers: `# hackathon-kit:begin` … `# hackathon-kit:end`. A server with the same name outside the block → `CONFLICT`, file untouched.
- MCP: only `sequential-thinking` is enabled, package `@modelcontextprotocol/server-sequential-thinking` pinned at `2026.8.31`, stdio, `npx -y <pkg>@<ver>`. `fetch`, `git`, `filesystem` are recorded with `enabled_by_default: false` and a reason, never registered.
- Allowlist: servers `["sequential-thinking"]`, commands `["npx", "uvx"]`, forbidden keys `["url", "bearer_token_env_var"]`, forbidden env name patterns `_API_KEY`, `_TOKEN`, `_SECRET` (suffix, case-insensitive).
- Tool pins: pytest `8.4.2`, ruff `0.17.3`. Install order `uv tool install <pkg>==<ver>` then `python -m pip install --user <pkg>==<ver>`; at most one retry per command; never require admin rights.
- data profile never installs numpy/pandas — advice only. web profile installs nothing. full profile reports only (no installs).
- `--offline`: no tool installs, no MCP handshake (`SKIPPED`), no network at all. `--no-mcp`: no config block, MCP items `SKIPPED`. `--dry-run`: writes nothing, runs no install, starts no server. MCP `SKIPPED` never degrades status.
- Report must say: "Codex loads .codex/config.toml only for trusted projects".
- Tests never start real `npx`, `uv`, `pip` or `codex`; autouse fixtures fake them unless a test is marked `real_mcp`.
- Lines ≤ 100 characters (ruff `E501` is enabled): wrap long string literals when transcribing plan code.
- Lint gate: `uv run ruff check .`, `uv run ruff format --check .`; `shellcheck bootstrap.sh` if the shell scripts change.
- Commit messages exactly as given; no AI attribution lines; never push.
- README/docs in Korean; code, comments, AGENTS.md/SKILL.md in English.

---

## File Structure

| File | Responsibility |
|---|---|
| `profiles/{python,data,web,full}.json` | New profiles (Task 1) |
| `kit/profiles.py` | Schema validation, `report_only` (Task 1) |
| `kit/agentsmd.py` | Marker parameters for the generic block merge (Task 2) |
| `mcp/manifest.json`, `mcp/allowlist.json` | MCP candidates and policy (Task 2) |
| `kit/mcpconfig.py` | Manifest/allowlist loading, TOML block render/check/verify (Task 2) |
| `kit/plan.py`, `kit/verify.py`, `kit/app.py` | Config block planning and verification (Task 3) |
| `kit/audit.py` | Config audit (Task 4) |
| `kit/tools.py` | Tool planning, install, re-probe (Task 5) |
| `kit/report.py` | Network line (Task 5), MCP line and next-action order (Task 7) |
| `kit/webcheck.py` | package.json / engines.node check (Task 6) |
| `kit/mcpcheck.py` | stdio handshake, `codex mcp list --json` (Task 7) |
| `devtools/make_examples.py`, `docs/examples/*.log`, `docs/*.md`, `README.md` | Docs and example logs (Task 8) |

---

### Task 1: Profile schema and the four new profiles

**Files:**
- Modify: `kit/profiles.py`
- Create: `profiles/python.json`, `profiles/data.json`, `profiles/web.json`, `profiles/full.json`
- Test: `tests/test_profiles.py`

**Interfaces:**
- Consumes: `kit.model.UsageError`.
- Produces: `Profile.report_only: bool` (default `False`); `KINDS = ("python-tool", "python-lib", "node-project")`; tool dicts are validated: `python-tool` has `name, kind, package, version, command`; `python-lib` has `name, kind, package`; `node-project` has `name, kind`. Malformed JSON or schema → `UsageError`.

- [ ] **Step 1: Update the existing extends test and add new failing tests**

In `tests/test_profiles.py`, replace the tool dicts in `test_extends_merges_lists_base_first` with valid ones:

```python
PYTEST = {"name": "pytest", "kind": "python-tool", "package": "pytest", "version": "1", "command": "pytest"}
RUFF = {"name": "ruff", "kind": "python-tool", "package": "ruff", "version": "1", "command": "ruff"}
```

use `"tools": [PYTEST]` in base, `"tools": [RUFF]` in child, and assert `profile.tools == [PYTEST, RUFF]`. Then append:

```python
def test_all_profiles_available(kit_root):
    assert available_profiles(kit_root) == ["core", "data", "full", "python", "web"]


def test_python_profile(kit_root):
    profile = load_profile(kit_root, "python")
    assert profile.skills == ALL_SKILLS
    assert [(t["name"], t["version"]) for t in profile.tools] == [("pytest", "8.4.2"), ("ruff", "0.17.3")]
    assert profile.mcp == ["sequential-thinking"]
    assert profile.report_only is False


def test_data_profile_only_advises_libraries(kit_root):
    profile = load_profile(kit_root, "data")
    kinds = {t["name"]: t["kind"] for t in profile.tools}
    assert kinds == {"pytest": "python-tool", "ruff": "python-tool", "numpy": "python-lib", "pandas": "python-lib"}


def test_web_profile(kit_root):
    profile = load_profile(kit_root, "web")
    assert [t["kind"] for t in profile.tools] == ["node-project"]
    assert profile.mcp == ["sequential-thinking"]


def test_full_profile_is_report_only(kit_root):
    profile = load_profile(kit_root, "full")
    assert profile.report_only is True
    assert {t["kind"] for t in profile.tools} == {"python-tool", "python-lib", "node-project"}
    assert profile.mcp == ["sequential-thinking"]


def test_report_only_is_not_inherited(tmp_path):
    _write(tmp_path, "base", {"name": "base", "report_only": True})
    _write(tmp_path, "child", {"name": "child", "extends": "base"})
    assert load_profile(tmp_path, "child").report_only is False


def test_malformed_json_is_usage_error(tmp_path):
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "bad.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(UsageError, match="not valid JSON"):
        load_profile(tmp_path, "bad")


@pytest.mark.parametrize(
    "data, message",
    [
        ({"name": "x", "extends": 3}, "extends"),
        ({"name": "x", "skills": "task-router"}, "skills"),
        ({"name": "x", "mcp": [1]}, "mcp"),
        ({"name": "x", "tools": [{"name": "t"}]}, "kind"),
        ({"name": "x", "tools": [{"name": "t", "kind": "python-tool", "package": "t"}]}, "version"),
        ({"name": "x", "tools": [{"name": "t", "kind": "python-lib"}]}, "package"),
        ({"name": "x", "report_only": "yes"}, "report_only"),
        (["not", "an", "object"], "object"),
    ],
)
def test_schema_errors_are_usage_errors(tmp_path, data, message):
    _write(tmp_path, "x", data)
    with pytest.raises(UsageError, match=message):
        load_profile(tmp_path, "x")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_profiles.py -v`
Expected: FAIL (unknown profiles, no `report_only`, no schema errors).

- [ ] **Step 3: Implement validation in `kit/profiles.py`**

Replace the module body below the imports with:

```python
LIST_KEYS = ("skills", "required_skills", "tools", "mcp")
NAME_LISTS = ("skills", "required_skills", "mcp")
KINDS = ("python-tool", "python-lib", "node-project")
REQUIRED_TOOL_KEYS = {
    "python-tool": ("package", "version", "command"),
    "python-lib": ("package",),
    "node-project": (),
}


@dataclass
class Profile:
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    mcp: list[str] = field(default_factory=list)
    report_only: bool = False


def available_profiles(kit_root: Path) -> list[str]:
    return sorted(path.stem for path in (kit_root / "profiles").glob("*.json"))


def _read(kit_root: Path, name: str) -> dict:
    path = kit_root / "profiles" / f"{name}.json"
    if not path.is_file():
        available = ", ".join(available_profiles(kit_root))
        raise UsageError(f"unknown profile '{name}' (available: {available})")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise UsageError(f"profile '{name}' is not valid JSON: {exc}") from exc
    _validate(name, data)
    return data


def _validate(name: str, data: object) -> None:
    if not isinstance(data, dict):
        raise UsageError(f"profile '{name}' must be a JSON object")
    extends = data.get("extends")
    if extends is not None and not isinstance(extends, str):
        raise UsageError(f"profile '{name}': extends must be a profile name or null")
    if not isinstance(data.get("report_only", False), bool):
        raise UsageError(f"profile '{name}': report_only must be true or false")
    for key in NAME_LISTS:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise UsageError(f"profile '{name}': {key} must be a list of names")
    tools = data.get("tools", [])
    if not isinstance(tools, list):
        raise UsageError(f"profile '{name}': tools must be a list")
    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            raise UsageError(f"profile '{name}': every tool needs a name")
        kind = tool.get("kind")
        if kind not in KINDS:
            raise UsageError(f"profile '{name}': tool '{tool['name']}' has unknown kind {kind!r}")
        for key in REQUIRED_TOOL_KEYS[kind]:
            if not isinstance(tool.get(key), str):
                raise UsageError(f"profile '{name}': tool '{tool['name']}' needs {key}")


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
    return Profile(
        name=name,
        description=chain[0].get("description", ""),
        report_only=chain[0].get("report_only", False),
        **merged,
    )
```

- [ ] **Step 4: Create the profiles**

`profiles/python.json`:

```json
{
  "name": "python",
  "description": "core plus pytest and ruff (installed only when missing) and the sequential-thinking MCP server.",
  "extends": "core",
  "tools": [
    {"name": "pytest", "kind": "python-tool", "package": "pytest", "version": "8.4.2", "command": "pytest"},
    {"name": "ruff", "kind": "python-tool", "package": "ruff", "version": "0.17.3", "command": "ruff"}
  ],
  "mcp": ["sequential-thinking"]
}
```

`profiles/data.json`:

```json
{
  "name": "data",
  "description": "python plus a check for numpy and pandas. Never installs them; prints the install command instead.",
  "extends": "python",
  "tools": [
    {"name": "numpy", "kind": "python-lib", "package": "numpy"},
    {"name": "pandas", "kind": "python-lib", "package": "pandas"}
  ]
}
```

`profiles/web.json`:

```json
{
  "name": "web",
  "description": "core plus a read-only check of the target's package.json, lockfile and engines.node, and the sequential-thinking MCP server. Installs nothing.",
  "extends": "core",
  "tools": [
    {"name": "node-project", "kind": "node-project"}
  ],
  "mcp": ["sequential-thinking"]
}
```

`profiles/full.json`:

```json
{
  "name": "full",
  "description": "Development only. Checks every candidate (python, data, web, MCP) and reports what it would install; installs no tools.",
  "extends": "data",
  "report_only": true,
  "tools": [
    {"name": "node-project", "kind": "node-project"}
  ]
}
```

- [ ] **Step 5: Run tests and lint**

Run: `uv run pytest -q` then `uv run ruff check . ; uv run ruff format --check .`
Expected: all pass. (`bootstrap.sh`/`bootstrap.ps1` already accept `core|python|data|web|full`.)

- [ ] **Step 6: Commit**

```bash
git add kit/profiles.py profiles/python.json profiles/data.json profiles/web.json profiles/full.json tests/test_profiles.py
git commit -m "feat: add python, data, web and full profiles with schema checks"
```

---

### Task 2: MCP manifest, allowlist and the TOML config block

**Files:**
- Modify: `kit/agentsmd.py`
- Create: `mcp/manifest.json`, `mcp/allowlist.json`, `kit/mcpconfig.py`
- Test: `tests/test_mcpconfig.py`, `tests/test_agentsmd.py` (one added test)

**Interfaces:**
- Consumes: `agentsmd.extract_block`, `agentsmd.MarkerError`, `kit.model`.
- Produces:
  - `agentsmd.render_block(body, begin=BEGIN, end=END)`, `agentsmd.extract_block(text, begin=BEGIN, end=END)`, `agentsmd.merge(existing, body, recorded_hash, begin=BEGIN, end=END)` — behaviour for AGENTS.md unchanged.
  - `mcpconfig.BEGIN = "# hackathon-kit:begin"`, `mcpconfig.END = "# hackathon-kit:end"`, `mcpconfig.CONFIG_REL = ".codex/config.toml"`, `mcpconfig.TRUST_NOTE`.
  - `load_manifest(kit_root) -> dict`, `load_allowlist(kit_root) -> dict`.
  - `select_servers(kit_root, names: list[str]) -> list[tuple[str, dict]]` (raises `UsageError` for a name not enabled in both files).
  - `render_servers(servers) -> str` (no trailing newline).
  - `parse_toml(text) -> tuple[bool | None, dict | None, str]` — `(True, data, "")`, `(False, None, error)`, or `(None, None, "")` when `tomllib` is unavailable.
  - `check_merged(new_text, names) -> str | None` — problem text or `None`.
  - `verify_config(target, kit_root, names, conflict_detail: str | None) -> ItemResult` named `mcp-config`, optional.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_agentsmd.py`:

```python
def test_custom_markers_round_trip():
    text, outcome, _ = merge("a = 1\n", "x = 2", None, "# b", "# e")
    assert outcome == "append"
    assert text == "a = 1\n\n# b\nx = 2\n# e\n"
    assert extract_block(text, "# b", "# e")[2] == "x = 2"
    assert extract_block(text) is None
```

(import `extract_block`, `merge` from `kit.agentsmd` if the file does not already.)

Create `tests/test_mcpconfig.py`:

```python
import pytest

from kit import mcpconfig
from kit.mcpconfig import (
    BEGIN,
    END,
    check_merged,
    load_allowlist,
    load_manifest,
    parse_toml,
    render_servers,
    select_servers,
    verify_config,
)
from kit.model import CONFLICT, FAIL, PASS, UNVERIFIED, UsageError

PKG = "@modelcontextprotocol/server-sequential-thinking"


def test_manifest_enables_only_pinned_sequential_thinking(kit_root):
    servers = load_manifest(kit_root)["servers"]
    enabled = sorted(n for n, e in servers.items() if e["enabled_by_default"])
    assert enabled == ["sequential-thinking"]
    entry = servers["sequential-thinking"]
    assert entry["package"] == PKG and entry["version"] == "2026.8.31"
    assert entry["command"] == "npx" and entry["args"] == ["-y", f"{PKG}@2026.8.31"]
    for name in ("fetch", "git", "filesystem"):
        assert servers[name]["enabled_by_default"] is False
        assert servers[name]["disabled_reason"]


def test_allowlist(kit_root):
    allow = load_allowlist(kit_root)
    assert allow["servers"] == ["sequential-thinking"]
    assert allow["commands"] == ["npx", "uvx"]
    assert allow["forbidden_keys"] == ["url", "bearer_token_env_var"]


def test_select_rejects_disabled_server(kit_root):
    with pytest.raises(UsageError, match="fetch"):
        select_servers(kit_root, ["fetch"])


def test_render_is_valid_toml(kit_root):
    body = render_servers(select_servers(kit_root, ["sequential-thinking"]))
    assert body.splitlines()[0] == "[mcp_servers.sequential-thinking]"
    status, data, _ = parse_toml(body)
    if status is None:
        pytest.skip("tomllib needs Python 3.11+")
    server = data["mcp_servers"]["sequential-thinking"]
    assert server["command"] == "npx"
    assert server["args"] == ["-y", f"{PKG}@2026.8.31"]


def test_check_merged_detects_outside_duplicate():
    text = f'[mcp_servers.sequential-thinking]\ncommand = "x"\n\n{BEGIN}\n[mcp_servers.sequential-thinking]\ncommand = "npx"\n{END}\n'
    assert "outside the kit block" in check_merged(text, ["sequential-thinking"])


def test_check_merged_detects_invalid_toml():
    if parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    text = f'model = \n{BEGIN}\n[mcp_servers.s]\ncommand = "npx"\n{END}\n'
    assert "not be valid TOML" in check_merged(text, ["s"])


def test_check_merged_accepts_clean_merge():
    text = f'model = "m"\n[mcp_servers.other]\ncommand = "uvx"\n\n{BEGIN}\n[mcp_servers.s]\ncommand = "npx"\n{END}\n'
    assert check_merged(text, ["s"]) is None


def _write_config(workspace, text):
    path = workspace / ".codex" / "config.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _kit_config(kit_root):
    return f"{BEGIN}\n{render_servers(select_servers(kit_root, ['sequential-thinking']))}\n{END}\n"


def test_verify_config_pass_mentions_trust(kit_root, workspace):
    _write_config(workspace, _kit_config(kit_root))
    item = verify_config(workspace, kit_root, ["sequential-thinking"], None)
    assert item.verified in (PASS, UNVERIFIED)
    assert "trusted projects" in item.detail


def test_verify_config_without_tomllib_is_unverified(kit_root, workspace, monkeypatch):
    _write_config(workspace, _kit_config(kit_root))
    monkeypatch.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))
    item = verify_config(workspace, kit_root, ["sequential-thinking"], None)
    assert item.verified == UNVERIFIED and "3.11" in item.detail


def test_verify_config_failures(kit_root, workspace):
    assert verify_config(workspace, kit_root, ["sequential-thinking"], None).verified == FAIL
    _write_config(workspace, f'{BEGIN}\n[mcp_servers.sequential-thinking]\ncommand = "old"\n{END}\n')
    item = verify_config(workspace, kit_root, ["sequential-thinking"], None)
    assert item.verified == FAIL and "outdated" in item.detail


def test_verify_config_conflict(kit_root, workspace):
    item = verify_config(workspace, kit_root, ["sequential-thinking"], "already defined")
    assert item.verified == CONFLICT and item.required is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_mcpconfig.py tests/test_agentsmd.py -v`
Expected: FAIL (`kit.mcpconfig` missing; `merge` takes no marker arguments).

- [ ] **Step 3: Add marker parameters to `kit/agentsmd.py`**

Change the three functions to (bodies otherwise identical; replace every `BEGIN`/`END` inside them with `begin`/`end`):

```python
def render_block(body: str, begin: str = BEGIN, end: str = END) -> str:
    return f"{begin}\n{body.strip()}\n{end}\n"


def extract_block(
    text: str, begin: str = BEGIN, end: str = END
) -> tuple[int, int, str] | None:
    """Return (start, stop, stripped interior) of the block, or None if there is none."""
    begins, ends = text.count(begin), text.count(end)
    if begins == 0 and ends == 0:
        return None
    if begins != 1 or ends != 1:
        raise MarkerError("expected exactly one begin and one end marker")
    start, stop_marker = text.index(begin), text.index(end)
    if stop_marker < start:
        raise MarkerError("end marker appears before begin marker")
    stop = stop_marker + len(end)
    if text.startswith("\r\n", stop):
        stop += 2
    elif text.startswith("\n", stop):
        stop += 1
    return start, stop, text[start + len(begin) : stop_marker].replace("\r\n", "\n").strip()


def merge(
    existing: str | None,
    body: str,
    recorded_hash: str | None,
    begin: str = BEGIN,
    end: str = END,
) -> tuple[str | None, str, str]:
    """Return (new text or None when nothing is written, outcome, detail)."""
    block = render_block(body, begin, end)
    if existing is None or not existing.strip():
        return block, Outcome.CREATE, ""
    try:
        found = extract_block(existing, begin, end)
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

Update the module docstring to: `"""Protected-block merge (AGENTS.md by default; markers are parameters), never touching other text."""`

- [ ] **Step 4: Create `mcp/manifest.json`**

```json
{
  "servers": {
    "sequential-thinking": {
      "package": "@modelcontextprotocol/server-sequential-thinking",
      "version": "2026.8.31",
      "license": "package says 'SEE LICENSE IN LICENSE' (modelcontextprotocol/servers); 2025.12.18 declared MIT. Not re-checked for 2026.8.31.",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2026.8.31"],
      "startup_timeout_sec": 30,
      "network_egress": "npm registry download on first start; the server itself is not expected to use the network (not verified)",
      "file_access": "none expected",
      "enabled_by_default": true,
      "disabled_reason": null,
      "version_note": "2.0.0 (2026-10-19) requires node >=24; 2026.8.31 declares no engines and was chosen for older exam machines"
    },
    "fetch": {
      "package": "mcp-server-fetch",
      "transport": "stdio",
      "enabled_by_default": false,
      "disabled_reason": "fetches arbitrary URLs: can send task data outside the workspace"
    },
    "git": {
      "package": "mcp-server-git",
      "transport": "stdio",
      "enabled_by_default": false,
      "disabled_reason": "exposes git operations; remote sync and push are forbidden in the exam"
    },
    "filesystem": {
      "package": "@modelcontextprotocol/server-filesystem",
      "transport": "stdio",
      "enabled_by_default": false,
      "disabled_reason": "duplicates Codex's own file access and widens the reachable paths"
    }
  }
}
```

- [ ] **Step 5: Create `mcp/allowlist.json`**

```json
{
  "servers": ["sequential-thinking"],
  "commands": ["npx", "uvx"],
  "forbidden_keys": ["url", "bearer_token_env_var"],
  "forbidden_env_patterns": ["(?i)_API_KEY$", "(?i)_TOKEN$", "(?i)_SECRET$"]
}
```

- [ ] **Step 6: Create `kit/mcpconfig.py`**

```python
"""MCP server data (manifest/allowlist) and the kit block inside <target>/.codex/config.toml."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .agentsmd import MarkerError, extract_block
from .model import CONFLICT, FAIL, PASS, UNVERIFIED, ItemResult, UsageError

BEGIN = "# hackathon-kit:begin"
END = "# hackathon-kit:end"
CONFIG_REL = ".codex/config.toml"
TRUST_NOTE = "Codex loads .codex/config.toml only for trusted projects"
_HEADER = re.compile(
    r'^[ \t]*\[[ \t]*mcp_servers[ \t]*\.[ \t]*"?([A-Za-z0-9_-]+)"?[ \t]*\]', re.MULTILINE
)


def _load(kit_root: Path, name: str) -> dict:
    return json.loads((kit_root / "mcp" / name).read_text(encoding="utf-8"))


def load_manifest(kit_root: Path) -> dict:
    return _load(kit_root, "manifest.json")


def load_allowlist(kit_root: Path) -> dict:
    return _load(kit_root, "allowlist.json")


def select_servers(kit_root: Path, names: list[str]) -> list[tuple[str, dict]]:
    if not names:
        return []
    servers = load_manifest(kit_root)["servers"]
    allowed = set(load_allowlist(kit_root)["servers"])
    selected = []
    for name in names:
        entry = servers.get(name)
        if entry is None or not entry.get("enabled_by_default") or name not in allowed:
            raise UsageError(
                f"MCP server '{name}' is not enabled in mcp/manifest.json and mcp/allowlist.json"
            )
        selected.append((name, entry))
    return selected


def render_servers(servers: list[tuple[str, dict]]) -> str:
    blocks = []
    for name, entry in servers:
        args = ", ".join(json.dumps(arg) for arg in entry["args"])
        blocks.append(
            "\n".join(
                [
                    f"[mcp_servers.{name}]",
                    f"command = {json.dumps(entry['command'])}",
                    f"args = [{args}]",
                    f"startup_timeout_sec = {int(entry.get('startup_timeout_sec', 30))}",
                ]
            )
        )
    return "\n\n".join(blocks)


def parse_toml(text: str) -> tuple[bool | None, dict | None, str]:
    """(True, data, "") parsed; (False, None, error) invalid; (None, None, "") no tomllib."""
    try:
        import tomllib
    except ImportError:
        return None, None, ""
    try:
        return True, tomllib.loads(text), ""
    except tomllib.TOMLDecodeError as exc:
        return False, None, str(exc)


def _without_block(text: str) -> str:
    found = extract_block(text, BEGIN, END)
    return text if found is None else text[: found[0]] + text[found[1] :]


def _preserved(old: dict, new: dict) -> bool:
    for key, value in old.items():
        if key == "mcp_servers" and isinstance(value, dict):
            new_servers = new.get("mcp_servers", {})
            if any(new_servers.get(name) != cfg for name, cfg in value.items()):
                return False
        elif new.get(key) != value:
            return False
    return True


def check_merged(new_text: str, names: list[str]) -> str | None:
    """Return why the merged config must not be written, or None when it is safe."""
    try:
        outside = _without_block(new_text)
    except MarkerError as exc:
        return str(exc)
    duplicates = sorted(set(_HEADER.findall(outside)) & set(names))
    if duplicates:
        return f"MCP server '{duplicates[0]}' is already defined outside the kit block"
    status, new_data, error = parse_toml(new_text)
    if status is False:
        return f"merged config.toml would not be valid TOML: {error}"
    if status:
        _, old_data, _ = parse_toml(outside)
        if old_data is not None and not _preserved(old_data, new_data):
            return "merging would change existing config.toml settings"
    return None


def verify_config(
    target: Path, kit_root: Path, names: list[str], conflict_detail: str | None
) -> ItemResult:
    label = "mcp-config"
    if conflict_detail:
        return ItemResult(label, False, True, False, CONFLICT, conflict_detail)
    path = target / CONFIG_REL
    if not path.is_file():
        return ItemResult(label, False, False, False, FAIL, f"{CONFIG_REL} missing")
    try:
        text = path.read_bytes().decode("utf-8")
        found = extract_block(text, BEGIN, END)
    except (OSError, UnicodeDecodeError, MarkerError) as exc:
        return ItemResult(label, False, True, False, FAIL, str(exc))
    if found is None:
        return ItemResult(label, False, True, False, FAIL, "kit block missing")
    if found[2] != render_servers(select_servers(kit_root, names)).strip():
        return ItemResult(label, False, True, True, FAIL, "kit block is outdated")
    status, _, error = parse_toml(text)
    if status is None:
        return ItemResult(
            label, False, True, True, UNVERIFIED, f"TOML parse check needs Python 3.11+; {TRUST_NOTE}"
        )
    if status is False:
        return ItemResult(label, False, True, True, FAIL, f"not valid TOML: {error}")
    return ItemResult(label, False, True, True, PASS, TRUST_NOTE)
```

`verify_config` must call `parse_toml` through the module global (as written) so the test's monkeypatch applies.

- [ ] **Step 7: Run tests and lint**

Run: `uv run pytest -q ; uv run ruff check . ; uv run ruff format --check .`
Expected: all pass (run `uv run ruff format .` first if only formatting differs).

- [ ] **Step 8: Commit**

```bash
git add kit/agentsmd.py kit/mcpconfig.py mcp/manifest.json mcp/allowlist.json tests/test_mcpconfig.py tests/test_agentsmd.py
git commit -m "feat: add MCP manifest, allowlist and config block rendering"
```

---

### Task 3: Plan, write and verify the `.codex/config.toml` block

**Files:**
- Modify: `kit/plan.py`, `kit/verify.py`, `kit/app.py`
- Test: `tests/test_mcp_registration.py`

**Interfaces:**
- Consumes: Task 2 `mcpconfig` API; Task 1 `Profile.mcp`.
- Produces:
  - `plan.plan_mcp_config(target, kit_root, names, state) -> FileChange` (owner `"mcp-config"`, rel `.codex/config.toml`).
  - `plan.plan_changes(target, kit_root, profile, state, include_mcp: bool = True)`.
  - `verify.verify_target(..., include_mcp: bool = False)` appends the `mcp-config` item when true.
  - In `app.run`: `include_mcp = bool(profile.mcp) and not opts.no_mcp`; `mcpconfig.select_servers(kit_root, profile.mcp)` is called inside the argument `try` so a bad server name exits 64.

- [ ] **Step 1: Write failing tests** — `tests/test_mcp_registration.py`

```python
import pytest
from conftest import tree_digest

from kit.mcpconfig import BEGIN, END

CONFIG = (".codex", "config.toml")


def _config(workspace):
    return workspace.joinpath(*CONFIG)


def _write(workspace, text):
    path = _config(workspace)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def test_python_profile_creates_config_block(run_kit, workspace):
    code, out = run_kit("--profile", "python")
    text = _config(workspace).read_text(encoding="utf-8")
    assert text.startswith(BEGIN) and END in text
    assert "[mcp_servers.sequential-thinking]" in text
    assert code == 0, out


def test_existing_settings_are_preserved_byte_for_byte(run_kit, workspace):
    original = 'model = "m"\n\n[mcp_servers.other]\ncommand = "uvx"\nargs = ["x"]\n'
    _write(workspace, original)
    run_kit("--profile", "python")
    text = _config(workspace).read_text(encoding="utf-8")
    assert text.startswith(original)
    assert "[mcp_servers.sequential-thinking]" in text
    assert list((workspace / ".kit" / "backups").rglob("config.toml"))


def test_same_name_outside_block_is_conflict(run_kit, workspace):
    original = '[mcp_servers.sequential-thinking]\ncommand = "node"\n'
    _write(workspace, original)
    code, out = run_kit("--profile", "python")
    assert _config(workspace).read_text(encoding="utf-8") == original
    assert "CONFLICT" in out and "outside the kit block" in out
    assert code == 1


def test_invalid_existing_toml_is_left_alone(run_kit, workspace):
    pytest.importorskip("tomllib")
    original = "model = \n"
    _write(workspace, original)
    code, out = run_kit("--profile", "python")
    assert _config(workspace).read_text(encoding="utf-8") == original
    assert code == 1 and "CONFLICT" in out


def test_edited_block_is_conflict(run_kit, workspace):
    run_kit("--profile", "python")
    path = _config(workspace)
    path.write_text(path.read_text(encoding="utf-8").replace("30", "99"), encoding="utf-8")
    edited = path.read_bytes()
    code, out = run_kit("--profile", "python")
    assert path.read_bytes() == edited
    assert code == 1 and "edited outside the kit" in out


def test_rerun_is_idempotent(run_kit, workspace):
    run_kit("--profile", "python")
    before = tree_digest(workspace)
    run_kit("--profile", "python")
    assert tree_digest(workspace) == before


def test_no_mcp_writes_no_config(run_kit, workspace):
    run_kit("--profile", "python", "--no-mcp")
    assert not (workspace / ".codex").exists()


def test_core_writes_no_config(run_kit, workspace):
    run_kit()
    assert not (workspace / ".codex").exists()


def test_dry_run_lists_config(run_kit, workspace):
    code, out = run_kit("--profile", "python", "--dry-run")
    assert code == 0 and "CREATE    .codex/config.toml" in out
    assert not (workspace / ".codex").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_mcp_registration.py -v`
Expected: FAIL (no config written).

- [ ] **Step 3: Refactor `kit/plan.py`**

Add `from . import agentsmd, mcpconfig` (replacing `from . import agentsmd`) and replace `plan_agents_md` with:

```python
def _plan_block(
    target: Path, rel: str, owner: str, body: str, state: State, begin: str, end: str
) -> FileChange:
    try:
        path = safe_path(target, rel)
        if path.exists() and not path.is_file():
            return FileChange(
                rel, owner, Outcome.CONFLICT, detail="exists but is not a regular file"
            )
        existing = path.read_bytes().decode("utf-8") if path.is_file() else None
    except PathEscapeError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=str(exc))
    except UnicodeDecodeError:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=f"existing {rel} is not UTF-8")
    except OSError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=f"cannot read {rel}: {exc}")
    text, outcome, detail = agentsmd.merge(existing, body, state.files.get(rel), begin, end)
    if outcome == Outcome.CONFLICT:
        return FileChange(rel, owner, outcome, detail=detail)
    data = text.encode("utf-8") if text is not None else None
    return FileChange(rel, owner, outcome, data, sha256(body.strip().encode("utf-8")), detail)


def plan_agents_md(target: Path, kit_root: Path, state: State) -> FileChange:
    body = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    return _plan_block(
        target, "AGENTS.md", "AGENTS.md", body, state, agentsmd.BEGIN, agentsmd.END
    )


def plan_mcp_config(target: Path, kit_root: Path, names: list[str], state: State) -> FileChange:
    body = mcpconfig.render_servers(mcpconfig.select_servers(kit_root, names))
    change = _plan_block(
        target, mcpconfig.CONFIG_REL, "mcp-config", body, state, mcpconfig.BEGIN, mcpconfig.END
    )
    if change.data is not None:
        problem = mcpconfig.check_merged(change.data.decode("utf-8"), names)
        if problem:
            return FileChange(change.rel, change.owner, Outcome.CONFLICT, detail=problem)
    return change
```

and change `plan_changes`:

```python
def plan_changes(
    target: Path, kit_root: Path, profile: Profile, state: State, include_mcp: bool = True
) -> list[FileChange]:
    changes = [plan_agents_md(target, kit_root, state)]
    for name in profile.skills:
        for rel, data in iter_skill_files(kit_root, name):
            changes.append(plan_file(target, rel, f"skill:{name}", data, state))
    if include_mcp and profile.mcp:
        changes.append(plan_mcp_config(target, kit_root, profile.mcp, state))
    return changes
```

- [ ] **Step 4: Extend `kit/verify.py`**

Add `from .mcpconfig import verify_config`, add the keyword parameter `include_mcp: bool = False` at the end of `verify_target`'s signature, and before `return items`:

```python
    if include_mcp and profile.mcp:
        items.append(
            verify_config(target, kit_root, profile.mcp, conflicts.get("mcp-config"))
        )
```

- [ ] **Step 5: Wire `kit/app.py`**

Add `from . import mcpconfig`. Inside the first `try` after `profile = load_profile(...)` add `mcpconfig.select_servers(kit_root, profile.mcp)`. After `state = State.load(...)`:

```python
    include_mcp = bool(profile.mcp) and not opts.no_mcp
    changes = plan_changes(opts.target, kit_root, profile, state, include_mcp)
```

and pass `include_mcp=include_mcp` to `verify_target(...)`.

- [ ] **Step 6: Run tests and lint**

Run: `uv run pytest -q ; uv run ruff check . ; uv run ruff format --check .`
Expected: all pass, including the Plan 1 suites (AGENTS.md detail strings are unchanged because `rel == "AGENTS.md"`).

- [ ] **Step 7: Commit**

```bash
git add kit/plan.py kit/verify.py kit/app.py tests/test_mcp_registration.py
git commit -m "feat: register MCP servers in the target .codex/config.toml block"
```

---

### Task 4: Security audit of the target config

**Files:**
- Create: `kit/audit.py`
- Modify: `kit/app.py`, `tests/test_security.py`
- Test: `tests/test_audit.py`

**Interfaces:**
- Consumes: `mcpconfig.parse_toml`, `mcpconfig.load_allowlist`, `mcpconfig.CONFIG_REL`.
- Produces: `audit.audit_config(data: dict, allowlist: dict) -> list[str]`; `audit.audit_target(target, kit_root) -> ItemResult` named `security audit`, **required** (FAIL → BLOCKED).

- [ ] **Step 1: Write failing tests** — `tests/test_audit.py`

```python
import pytest

from kit import mcpconfig
from kit.audit import audit_config, audit_target
from kit.model import FAIL, PASS, UNVERIFIED

ALLOW = {
    "servers": ["sequential-thinking"],
    "commands": ["npx", "uvx"],
    "forbidden_keys": ["url", "bearer_token_env_var"],
    "forbidden_env_patterns": ["(?i)_API_KEY$", "(?i)_TOKEN$", "(?i)_SECRET$"],
}
GOOD = {"command": "npx", "args": ["-y", "pkg@1"]}


def _servers(**cfg):
    return {"mcp_servers": {"sequential-thinking": {**GOOD, **cfg}}}


def test_allowlisted_server_passes():
    assert audit_config(_servers(), ALLOW) == []


def test_windows_command_suffix_is_normalised():
    assert audit_config(_servers(command="C:\\node\\npx.cmd"), ALLOW) == []


@pytest.mark.parametrize(
    "data, fragment",
    [
        ({"mcp_servers": {"other": GOOD}}, "not in mcp/allowlist.json"),
        (_servers(url="https://example.invalid/mcp"), "forbidden key 'url'"),
        (_servers(bearer_token_env_var="X"), "forbidden key 'bearer_token_env_var'"),
        (_servers(command="bash"), "command 'bash' is not allowed"),
        (_servers(args=["https://example.invalid"]), "remote endpoint"),
        (_servers(env={"OPENAI_API_KEY": "x"}), "secret-like env 'OPENAI_API_KEY'"),
        (_servers(env_vars=["GITHUB_TOKEN"]), "secret-like env 'GITHUB_TOKEN'"),
        ({"mcp_servers": "oops"}, "mcp_servers must be a table"),
    ],
)
def test_violations(data, fragment):
    problems = audit_config(data, ALLOW)
    assert any(fragment in p for p in problems), problems


def _write(workspace, text):
    path = workspace / ".codex" / "config.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_no_config_passes(kit_root, workspace):
    assert audit_target(workspace, kit_root).verified == PASS


def test_remote_server_fails(kit_root, workspace):
    if mcpconfig.parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    _write(workspace, '[mcp_servers.remote]\nurl = "https://example.invalid/mcp"\n')
    item = audit_target(workspace, kit_root)
    assert item.verified == FAIL and item.required is True
    assert "remote" in item.detail


def test_without_tomllib_is_unverified(kit_root, workspace, monkeypatch):
    _write(workspace, '[mcp_servers.remote]\nurl = "https://example.invalid/mcp"\n')
    monkeypatch.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))
    assert audit_target(workspace, kit_root).verified == UNVERIFIED


def test_remote_server_blocks_the_run(run_kit, workspace):
    if mcpconfig.parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    _write(workspace, '[mcp_servers.remote]\nurl = "https://example.invalid/mcp"\n')
    code, out = run_kit()
    assert code == 2 and "security audit" in out

```

In `tests/test_security.py`, extend the scanned files and patterns:

```python
FORBIDDEN = [
    re.compile(r"git\s+push"),
    re.compile(r"curl[^\n|]*\|\s*(ba)?sh"),
    re.compile(r"\|\s*iex\b", re.IGNORECASE),
    re.compile(r"Invoke-Expression", re.IGNORECASE),
    re.compile(r"https?://[^\s\"']*(telemetry|analytics|sentry|segment)", re.IGNORECASE),
]
CODE_GLOBS = [
    "kit/*.py", "run_kit.py", "bootstrap.sh", "bootstrap.ps1", "mcp/*.json", "profiles/*.json",
]
```

and add:

```python
def test_kit_mcp_data_contains_no_remote_endpoints(kit_root):
    for path in kit_root.glob("mcp/*.json"):
        assert not re.search(r"https?://", path.read_text(encoding="utf-8")), path.name
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_audit.py tests/test_security.py -v`
Expected: FAIL (`kit.audit` missing).

- [ ] **Step 3: Create `kit/audit.py`**

```python
"""Audit the target's MCP config against mcp/allowlist.json. Reduces risk; not a guarantee."""

from __future__ import annotations

import re
from pathlib import Path

from . import mcpconfig
from .model import FAIL, PASS, UNVERIFIED, ItemResult

LABEL = "security audit"
_REMOTE = re.compile(r"https?://", re.IGNORECASE)


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _command_name(command: object) -> str:
    name = Path(str(command)).name.lower()
    for suffix in (".cmd", ".exe", ".bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def audit_config(data: dict, allowlist: dict) -> list[str]:
    servers = data.get("mcp_servers", {})
    if not isinstance(servers, dict):
        return ["mcp_servers must be a table"]
    patterns = [re.compile(p) for p in allowlist["forbidden_env_patterns"]]
    problems = []
    for name, cfg in servers.items():
        if name not in allowlist["servers"]:
            problems.append(f"{name}: not in mcp/allowlist.json")
        if not isinstance(cfg, dict):
            problems.append(f"{name}: must be a table")
            continue
        for key in allowlist["forbidden_keys"]:
            if key in cfg:
                problems.append(f"{name}: forbidden key '{key}' (remote transport)")
        command = cfg.get("command")
        if command is not None and _command_name(command) not in allowlist["commands"]:
            problems.append(f"{name}: command '{command}' is not allowed")
        for text in _strings(cfg):
            if _REMOTE.search(text):
                problems.append(f"{name}: remote endpoint '{text}'")
        env = cfg.get("env")
        env_names = list(env) if isinstance(env, dict) else []
        env_vars = cfg.get("env_vars")
        if isinstance(env_vars, list):
            env_names += [v for v in env_vars if isinstance(v, str)]
        for env_name in env_names:
            if any(p.search(env_name) for p in patterns):
                problems.append(f"{name}: secret-like env '{env_name}'")
    return problems


def audit_target(target: Path, kit_root: Path) -> ItemResult:
    path = target / mcpconfig.CONFIG_REL
    if not path.is_file():
        return ItemResult(LABEL, True, True, True, PASS, f"no {mcpconfig.CONFIG_REL}")
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return ItemResult(LABEL, True, True, False, FAIL, f"cannot read config: {exc}")
    status, data, error = mcpconfig.parse_toml(text)
    if status is None:
        return ItemResult(
            LABEL, True, True, False, UNVERIFIED, "config audit needs Python 3.11+ (tomllib)"
        )
    if status is False:
        return ItemResult(
            LABEL, True, True, False, UNVERIFIED, f"cannot audit: config is not valid TOML ({error})"
        )
    problems = audit_config(data, mcpconfig.load_allowlist(kit_root))
    if problems:
        more = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
        return ItemResult(LABEL, True, True, True, FAIL, "; ".join(problems[:3]) + more)
    return ItemResult(LABEL, True, True, True, PASS, "MCP config matches the allowlist")
```

- [ ] **Step 4: Wire into `kit/app.py`**

Add `from . import audit, mcpconfig` (merge with the existing `mcpconfig` import) and right after `items = verify_target(...)`:

```python
    items.append(audit.audit_target(opts.target, kit_root))
```

- [ ] **Step 5: Run tests and lint**

Run: `uv run pytest -q ; uv run ruff check . ; uv run ruff format --check .`
Expected: all pass. Core runs stay READY (`no .codex/config.toml` → PASS).

- [ ] **Step 6: Commit**

```bash
git add kit/audit.py kit/app.py tests/test_audit.py tests/test_security.py
git commit -m "feat: audit the target MCP config against the allowlist"
```

---

### Task 5: Profile tools (check, install, report)

**Files:**
- Create: `kit/tools.py`
- Modify: `kit/app.py`, `kit/report.py`, `tests/conftest.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `preflight.probe_tool(name)` (called through the module so `fast_preflight` fakes it), `EnvReport.tools["uv"]`, `Profile.tools`, `Profile.report_only`.
- Produces:
  - `tools.run_command(cmd, timeout=600.0, cwd=None) -> tuple[int, str]` (stdout+stderr; `(127, message)` on OSError/timeout).
  - `ToolAction(name, kind, status, command="", commands=[], detail="")`, statuses `present | install | missing | offline | advice | report`.
  - `plan_tools(profile, env, offline, verify_only) -> list[ToolAction]` (skips `node-project`).
  - `run_tools(actions, runner=None) -> list[ItemResult]` named `tool:<name>`, optional.
  - `format_tool_plan(actions) -> str`, `network_used(actions) -> list[str]`, `show(cmd) -> str`.
  - `report.render(..., network: str | None = None)` — when given, printed as `Network:      <network>`.
  - conftest autouse `no_real_commands` replaces `tools.run_command` with a fake returning `(1, "real commands are disabled in tests")`.

- [ ] **Step 1: Add the conftest guard**

In `tests/conftest.py` add `from kit import tools` and:

```python
@pytest.fixture(autouse=True)
def no_real_commands(monkeypatch):
    """Tool installs and codex calls never run for real in tests."""
    monkeypatch.setattr(
        tools,
        "run_command",
        lambda cmd, timeout=600.0, cwd=None: (1, "real commands are disabled in tests"),
    )
```

- [ ] **Step 2: Write failing tests** — `tests/test_tools.py`

```python
import sys

import pytest

from kit import preflight, tools
from kit.model import FAIL, PASS, SKIPPED, UNVERIFIED
from kit.preflight import EnvReport, ToolInfo
from kit.profiles import Profile
from kit.tools import plan_tools, run_tools

PYTEST = {"name": "pytest", "kind": "python-tool", "package": "pytest", "version": "8.4.2", "command": "pytest"}


def env(uv=True):
    tool_map = {"uv": ToolInfo("uv", "/fake/uv", "uv 1") if uv else ToolInfo("uv")}
    return EnvReport("os", "arch", "sh", "3.12", True, tool_map)


def profile(*specs, report_only=False):
    return Profile("p", "", tools=list(specs), report_only=report_only)


@pytest.fixture
def probe(monkeypatch):
    """Make pytest missing until `installed` is set."""
    state = {"installed": False}

    def fake(name, timeout=15.0):
        return ToolInfo(name, f"/fake/{name}", "9.9") if state["installed"] else ToolInfo(name)

    monkeypatch.setattr(preflight, "probe_tool", fake)
    return state


class Runner:
    def __init__(self, results, probe_state=None):
        self.results = list(results)
        self.calls = []
        self.probe_state = probe_state

    def __call__(self, cmd, timeout=600.0, cwd=None):
        self.calls.append(cmd)
        code, out = self.results.pop(0)
        if code == 0 and self.probe_state is not None:
            self.probe_state["installed"] = True
        return code, out


def test_present_tool_passes_without_running(probe):
    probe["installed"] = True
    runner = Runner([])
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert item.name == "tool:pytest" and item.verified == PASS and runner.calls == []


def test_install_with_uv(probe):
    runner = Runner([(0, "ok")], probe)
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert runner.calls == [["/fake/uv", "tool", "install", "pytest==8.4.2"]]
    assert item.verified == PASS and "uv tool install pytest==8.4.2" in item.detail


def test_uv_retried_once_then_pip(probe):
    runner = Runner([(1, "boom"), (1, "boom"), (0, "ok")], probe)
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    pip = [sys.executable, "-m", "pip", "install", "--user", "pytest==8.4.2"]
    assert runner.calls[2] == pip and len(runner.calls) == 3
    assert item.verified == PASS


def test_all_attempts_fail(probe):
    runner = Runner([(1, "a"), (1, "b"), (1, "c"), (1, "network down\n")])
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert len(runner.calls) == 4
    assert item.verified == FAIL and item.detail == "install failed: network down"


def test_installed_but_not_on_path_is_unverified(probe):
    runner = Runner([(0, "ok")])  # probe never flips
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert item.verified == UNVERIFIED and "not on PATH" in item.detail


def test_without_uv_only_pip(probe):
    [action] = plan_tools(profile(PYTEST), env(uv=False), False, False)
    assert [c[1:3] for c in action.commands] == [["-m", "pip"]]


@pytest.mark.parametrize(
    "offline, verify_only, report_only, verdict, fragment",
    [
        (True, False, False, SKIPPED, "offline"),
        (False, True, False, FAIL, "--verify-only"),
        (False, False, True, SKIPPED, "would run"),
    ],
)
def test_no_install_modes(probe, offline, verify_only, report_only, verdict, fragment):
    runner = Runner([])
    actions = plan_tools(profile(PYTEST, report_only=report_only), env(), offline, verify_only)
    [item] = run_tools(actions, runner)
    assert runner.calls == [] and item.verified == verdict and fragment in item.detail


def test_python_lib_is_advice_only():
    present = {"name": "json", "kind": "python-lib", "package": "json"}
    missing = {"name": "nope", "kind": "python-lib", "package": "kit_no_such_package_xyz"}
    a, b = run_tools(plan_tools(profile(present, missing), env(), False, False), Runner([]))
    assert a.verified == PASS
    assert b.verified == SKIPPED and "pip install --user kit_no_such_package_xyz" in b.detail


def test_node_project_is_not_a_tool_action():
    assert plan_tools(profile({"name": "n", "kind": "node-project"}), env(), False, False) == []


def test_network_used_lists_planned_installs(probe):
    actions = plan_tools(profile(PYTEST), env(), False, False)
    assert tools.network_used(actions) == ["uv tool install pytest==8.4.2"]
    assert "INSTALL" in tools.format_tool_plan(actions)


def test_python_profile_end_to_end_reports_network_not_used(run_kit):
    code, out = run_kit("--profile", "python", "--no-mcp")
    assert code == 0, out
    assert "Network:      not used" in out


def test_dry_run_shows_install_and_runs_nothing(run_kit, workspace, probe, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("dry-run must not run commands")

    monkeypatch.setattr(tools, "run_command", forbidden)
    code, out = run_kit("--profile", "python", "--dry-run")
    assert code == 0
    assert "INSTALL   tool:pytest" in out
    assert "Network:      would use:" in out and "pytest==8.4.2" in out
    assert list(workspace.iterdir()) == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_tools.py -v`
Expected: FAIL (`kit.tools` missing).

- [ ] **Step 4: Create `kit/tools.py`**

```python
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


def run_command(
    cmd: list[str], timeout: float = 600.0, cwd: Path | None = None
) -> tuple[int, str]:
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
```

(`run_tools` resolves `run_command` at call time, so the conftest patch applies.)

- [ ] **Step 5: Add the `network` parameter to `kit/report.render`**

Change the signature to `render(env, opts, items, status, actions, network: str | None = None)` and replace the `network = ...` line with:

```python
    if network is None:
        network = "not used (--offline)" if opts.offline else "not used"
```

- [ ] **Step 6: Wire into `kit/app.py`**

Add `from . import tools`. After `changes = plan_changes(...)`:

```python
    actions = tools.plan_tools(profile, env, opts.offline, opts.verify_only)
```

Change the dry-run call to `_dry_run_text(opts, env, changes, actions, profile)` and replace `_dry_run_text` with:

```python
def _dry_run_text(
    opts: Options, env: EnvReport, changes: list[FileChange], actions, profile
) -> str:
    planned = tools.network_used(actions)
    if opts.offline:
        network = "none (--offline)"
    elif planned:
        network = "would use: " + "; ".join(planned)
    elif not profile.tools and not profile.mcp:
        network = "none (this profile installs no tools)"
    else:
        network = "none"
    lines = [
        f"Environment:  {env.os} {env.arch}, shell={env.shell}, python {env.python}",
        f"Target:       {opts.target}",
        f"Profile:      {opts.profile}",
        f"Network:      {network}",
        "Planned changes:",
        format_plan(changes, opts.verbose),
    ]
    if actions:
        lines += ["Planned tools:", tools.format_tool_plan(actions)]
    lines += ["DRY RUN: nothing was written.", ""]
    return "\n".join(lines)
```

After the `apply_changes` block (before `verify_target`):

```python
    tool_items = tools.run_tools(actions)
```

After the audit line: `items.extend(tool_items)`. Then compute and pass the network line:

```python
    network = _network_line(opts, actions)
    lines.append(
        render(env, opts, items, status, next_actions(items, opts.target, status), network)
    )
```

with

```python
def _network_line(opts: Options, actions) -> str:
    if opts.offline:
        return "not used (--offline)"
    used = tools.network_used(actions)
    return "used: " + "; ".join(used) if used else "not used"
```

(`overall_status(items)` must be computed after `items.extend(tool_items)`.)

- [ ] **Step 7: Run tests and lint**

Run: `uv run pytest -q ; uv run ruff check . ; uv run ruff format --check .`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add kit/tools.py kit/app.py kit/report.py tests/conftest.py tests/test_tools.py
git commit -m "feat: check and install profile tools with uv and pip fallback"
```

---

### Task 6: web profile check (package.json and engines.node)

**Files:**
- Create: `kit/webcheck.py`
- Modify: `kit/app.py`
- Test: `tests/test_webcheck.py`

**Interfaces:**
- Consumes: `EnvReport.tools["node"]` (`ToolInfo`).
- Produces: `webcheck.parse_version(text) -> tuple[int, int, int] | None`; `webcheck.satisfies(version, spec) -> bool | None` (`None` = cannot evaluate); `webcheck.check_node_project(target, node: ToolInfo | None) -> ItemResult` named `node-project`, optional.

- [ ] **Step 1: Write failing tests** — `tests/test_webcheck.py`

```python
import json

import pytest

from kit.model import FAIL, PASS, SKIPPED, UNVERIFIED
from kit.preflight import ToolInfo
from kit.webcheck import check_node_project, parse_version, satisfies

NODE = ToolInfo("node", "/fake/node", "v20.11.1")


@pytest.mark.parametrize(
    "spec, expected",
    [
        (">=18", True),
        (">=21", False),
        (">18.0.0", True),
        (">20", False),
        ("<21", True),
        ("<=20", True),
        ("<20", False),
        ("^20.1", True),
        ("^21", False),
        ("^0.1.0", False),
        ("~20.11.0", True),
        ("~20.10", False),
        ("20", True),
        ("20.x", True),
        ("18.x || 20.x", True),
        (">=16 <19", False),
        ("*", True),
        ("", True),
        ("1.0.0 - 2.0.0", None),
        ("lts/*", None),
    ],
)
def test_satisfies(spec, expected):
    assert satisfies((20, 11, 1), spec) is expected


def test_parse_version():
    assert parse_version("v20.11.1") == (20, 11, 1)
    assert parse_version("node") is None


def _pkg(workspace, data):
    (workspace / "package.json").write_text(json.dumps(data), encoding="utf-8")


def test_no_package_json_is_skipped(workspace):
    assert check_node_project(workspace, NODE).verified == SKIPPED


def test_matching_engines_pass_and_list_lockfile(workspace):
    _pkg(workspace, {"engines": {"node": ">=18"}})
    (workspace / "package-lock.json").write_text("{}", encoding="utf-8")
    item = check_node_project(workspace, NODE)
    assert item.verified == PASS and "package-lock.json" in item.detail


def test_mismatch_fails(workspace):
    _pkg(workspace, {"engines": {"node": ">=22"}})
    item = check_node_project(workspace, NODE)
    assert item.verified == FAIL and ">=22" in item.detail


def test_unparseable_range_is_unverified(workspace):
    _pkg(workspace, {"engines": {"node": "lts/*"}})
    assert check_node_project(workspace, NODE).verified == UNVERIFIED


def test_missing_node_fails(workspace):
    _pkg(workspace, {})
    assert check_node_project(workspace, ToolInfo("node")).verified == FAIL


def test_invalid_json_fails(workspace):
    (workspace / "package.json").write_text("{", encoding="utf-8")
    assert check_node_project(workspace, NODE).verified == FAIL


def test_web_profile_end_to_end(run_kit, workspace):
    _pkg(workspace, {"engines": {"node": ">=1"}})
    code, out = run_kit("--profile", "web", "--verbose")
    assert "node-project" in out
    assert code in (0, 1), out
```

(`fast_preflight` reports node as `fake 1.0`, which is not an `x.y.z` version, so the item is UNVERIFIED here; the e2e only proves the item is wired in and does not block.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_webcheck.py -v`
Expected: FAIL (`kit.webcheck` missing).

- [ ] **Step 3: Create `kit/webcheck.py`**

```python
"""web profile: read package.json and check node against engines.node. Installs nothing."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .model import FAIL, PASS, SKIPPED, UNVERIFIED, ItemResult
from .preflight import ToolInfo

LABEL = "node-project"
LOCKFILES = (
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
)
_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
_COMPARATOR = re.compile(r"^(>=|<=|>|<|=|\^|~)?v?(\d+|x|\*)(?:\.(\d+|x|\*))?(?:\.(\d+|x|\*))?$")


def parse_version(text: str | None) -> tuple[int, int, int] | None:
    match = _VERSION.search(text or "")
    if not match:
        return None
    major, minor, patch = (int(g) for g in match.groups())
    return major, minor, patch


def _upper_caret(nums: list[int]) -> tuple[int, ...]:
    index = next((i for i, n in enumerate(nums) if n > 0), len(nums) - 1)
    bumped = nums[:index] + [nums[index] + 1]
    return tuple(bumped + [0] * (3 - len(bumped)))


def _match(version: tuple[int, int, int], comparator: str) -> bool | None:
    match = _COMPARATOR.match(comparator)
    if not match:
        return None
    op, *raw = match.groups()
    nums: list[int] = []
    for part in raw:
        if part is None or part in ("x", "*"):
            break
        nums.append(int(part))
    if not nums:
        return True
    prefix, wanted = version[: len(nums)], tuple(nums)
    base = tuple(nums + [0] * (3 - len(nums)))
    if op in (None, "="):
        return prefix == wanted
    if op == ">=":
        return prefix >= wanted
    if op == ">":
        return prefix > wanted
    if op == "<=":
        return prefix <= wanted
    if op == "<":
        return prefix < wanted
    if op == "^":
        return base <= version < _upper_caret(nums)
    upper = (nums[0], nums[1] + 1, 0) if len(nums) >= 2 else (nums[0] + 1, 0, 0)
    return base <= version < upper


def satisfies(version: tuple[int, int, int], spec: str) -> bool | None:
    spec = spec.strip()
    if spec in ("", "*", "x"):
        return True
    results = []
    for alternative in spec.split("||"):
        parts = alternative.split()
        if not parts:
            return None
        verdicts = [_match(version, part) for part in parts]
        if any(v is None for v in verdicts):
            return None
        results.append(all(verdicts))
    return any(results)


def check_node_project(target: Path, node: ToolInfo | None) -> ItemResult:
    path = target / "package.json"
    if not path.is_file():
        return ItemResult(LABEL, False, False, False, SKIPPED, "no package.json in target")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return ItemResult(LABEL, False, True, False, FAIL, f"package.json is not valid JSON: {exc}")
    locks = [name for name in LOCKFILES if (target / name).is_file()]
    lock_text = f"lockfiles: {', '.join(locks)}" if locks else "no lockfile"
    if node is None or not node.ok:
        return ItemResult(LABEL, False, True, False, FAIL, f"node not found; {lock_text}")
    engines = data.get("engines") if isinstance(data, dict) else None
    spec = engines.get("node") if isinstance(engines, dict) else None
    if not isinstance(spec, str):
        return ItemResult(LABEL, False, True, True, PASS, f"node {node.version}; {lock_text}")
    version = parse_version(node.version)
    verdict = satisfies(version, spec) if version else None
    if verdict is None:
        detail = f"cannot evaluate engines.node '{spec}' against {node.version}; {lock_text}"
        return ItemResult(LABEL, False, True, True, UNVERIFIED, detail)
    if not verdict:
        detail = f"node {node.version} does not satisfy engines.node '{spec}'; {lock_text}"
        return ItemResult(LABEL, False, True, True, FAIL, detail)
    return ItemResult(LABEL, False, True, True, PASS, f"node {node.version} satisfies '{spec}'; {lock_text}")
```

- [ ] **Step 4: Wire into `kit/app.py`**

Add `from . import webcheck`; after `items.extend(tool_items)`:

```python
    if any(spec["kind"] == "node-project" for spec in profile.tools):
        items.append(webcheck.check_node_project(opts.target, env.tools.get("node")))
```

- [ ] **Step 5: Run tests and lint**

Run: `uv run pytest -q ; uv run ruff check . ; uv run ruff format --check .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add kit/webcheck.py kit/app.py tests/test_webcheck.py
git commit -m "feat: check the target package.json against the local node"
```

---

### Task 7: MCP handshake, Codex listing and report lines

**Files:**
- Create: `kit/mcpcheck.py`
- Modify: `kit/app.py`, `kit/report.py`, `tests/conftest.py`, `pyproject.toml`, `tests/test_report.py`
- Test: `tests/test_mcpcheck.py`

**Interfaces:**
- Consumes: `mcpconfig.select_servers`, `tools.run_command` (via module), `EnvReport.tools["codex"]`.
- Produces:
  - `mcpcheck.find_command(name) -> str | None`.
  - `mcpcheck.handshake(command, timeout=120.0) -> tuple[str, str]` (PASS/FAIL, detail).
  - `mcpcheck.codex_lists(codex_path, target, name, runner=None) -> bool | None`.
  - `mcpcheck.check_servers(kit_root, names, env, target, offline, no_mcp) -> list[ItemResult]` — `mcp:<name>` and `codex-mcp:<name>`, optional.
  - `report.render` MCP line from `mcp:` items; `report.next_actions` orders required problems first and adds a trust action.
  - conftest autouse `fake_mcp` (skipped for tests marked `real_mcp`).

- [ ] **Step 1: Register the marker and the conftest fake**

`pyproject.toml` markers:

```toml
markers = [
  "real_preflight: run real tool probes instead of the fast fake",
  "real_mcp: run real MCP handshakes (against local fake servers only)",
]
```

`tests/conftest.py`: add `from kit import mcpcheck` and `from kit.model import PASS`, and:

```python
@pytest.fixture(autouse=True)
def fake_mcp(request, monkeypatch):
    """Never start npx or codex in tests unless marked real_mcp."""
    if request.node.get_closest_marker("real_mcp"):
        return
    monkeypatch.setattr(mcpcheck, "find_command", lambda name: f"/fake/{name}")
    monkeypatch.setattr(
        mcpcheck, "handshake", lambda command, timeout=120.0: (PASS, "1 tool(s): fake")
    )
    monkeypatch.setattr(
        mcpcheck, "codex_lists", lambda codex_path, target, name, runner=None: None
    )
```

- [ ] **Step 2: Write failing tests** — `tests/test_mcpcheck.py`

```python
import json
import socket
import sys

import pytest

from kit import mcpcheck
from kit.mcpcheck import check_servers, codex_lists, handshake
from kit.model import FAIL, PASS, SKIPPED, UNVERIFIED
from kit.preflight import EnvReport, ToolInfo

FAKE_SERVER = r"""
import json, sys
mode = sys.argv[1]
if mode == "exit":
    sys.exit(0)
for line in sys.stdin:
    msg = json.loads(line)
    if mode == "silent":
        continue
    if msg.get("method") == "initialize":
        print("starting up (log noise)", flush=True)
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {
            "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
            "serverInfo": {"name": "fake", "version": "0"}}}), flush=True)
    elif msg.get("method") == "tools/list":
        tools = [] if mode == "empty" else [{"name": "think", "inputSchema": {"type": "object"}}]
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": tools}}), flush=True)
"""


@pytest.fixture
def server(tmp_path):
    path = tmp_path / "fake_server.py"
    path.write_text(FAKE_SERVER, encoding="utf-8")
    return lambda mode: [sys.executable, str(path), mode]


@pytest.mark.real_mcp
def test_handshake_pass(server):
    assert handshake(server("ok"), timeout=30) == (PASS, "1 tool(s): think")


@pytest.mark.real_mcp
@pytest.mark.parametrize(
    "mode, fragment",
    [("empty", "no tools"), ("exit", "exited"), ("silent", "no response")],
)
def test_handshake_failures(server, mode, fragment):
    verdict, detail = handshake(server(mode), timeout=3)
    assert verdict == FAIL and fragment in detail


@pytest.mark.real_mcp
def test_handshake_missing_command():
    verdict, detail = handshake(["/definitely/not/here"], timeout=3)
    assert verdict == FAIL and "cannot start" in detail


def test_codex_lists_parses_json_with_noise(tmp_path):
    listing = json.dumps([{"name": "sequential-thinking"}, {"name": "other"}])
    runner = lambda cmd, timeout=60.0, cwd=None: (0, listing + "\nwarning: something\n")  # noqa: E731
    assert codex_lists("/fake/codex", tmp_path, "sequential-thinking", runner) is True
    assert codex_lists("/fake/codex", tmp_path, "missing", runner) is False
    failing = lambda cmd, timeout=60.0, cwd=None: (1, "")  # noqa: E731
    assert codex_lists("/fake/codex", tmp_path, "x", failing) is None


def env(codex=True):
    codex_info = ToolInfo("codex", "/fake/codex", "codex 1") if codex else ToolInfo("codex")
    return EnvReport("os", "arch", "sh", "3.12", True, {"codex": codex_info})


NAMES = ["sequential-thinking"]


def test_offline_and_no_mcp_skip(kit_root, workspace):
    [a] = check_servers(kit_root, NAMES, env(), workspace, True, False)
    [b] = check_servers(kit_root, NAMES, env(), workspace, False, True)
    assert a.verified == SKIPPED and "offline" in a.detail
    assert b.verified == SKIPPED and "--no-mcp" in b.detail


def test_missing_npx_fails(kit_root, workspace, monkeypatch):
    monkeypatch.setattr(mcpcheck, "find_command", lambda name: None)
    [item] = check_servers(kit_root, NAMES, env(), workspace, False, False)
    assert item.verified == FAIL and "npx not found" in item.detail


def test_handshake_and_codex_listing(kit_root, workspace, monkeypatch):
    seen = {}

    def fake_handshake(command, timeout=120.0):
        seen["command"] = command
        return PASS, "1 tool(s): think"

    monkeypatch.setattr(mcpcheck, "handshake", fake_handshake)
    monkeypatch.setattr(mcpcheck, "codex_lists", lambda *a, **k: True)
    mcp, codex = check_servers(kit_root, NAMES, env(), workspace, False, False)
    assert seen["command"][1:] == ["-y", "@modelcontextprotocol/server-sequential-thinking@2026.8.31"]
    assert (mcp.name, mcp.verified) == ("mcp:sequential-thinking", PASS)
    assert (codex.name, codex.verified) == ("codex-mcp:sequential-thinking", PASS)


def test_codex_not_listing_is_unverified(kit_root, workspace):
    _, codex = check_servers(kit_root, NAMES, env(), workspace, False, False)
    assert codex.verified == UNVERIFIED and "trust" in codex.detail


def test_python_profile_report_lines(run_kit):
    code, out = run_kit("--profile", "python")
    assert code == 0, out
    assert "MCP:          sequential-thinking PASS" in out
    assert "Network:      used: npx (MCP handshake)" in out
    assert "Trust" in out


def test_offline_python_profile_uses_no_network(run_kit, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline must not start servers")

    monkeypatch.setattr(mcpcheck, "handshake", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    code, out = run_kit("--profile", "python", "--offline")
    assert code == 0, out
    assert "MCP:          sequential-thinking SKIPPED" in out
    assert "Network:      not used (--offline)" in out
```

Add to `tests/test_report.py`:

```python
def test_next_actions_required_first_and_trust(tmp_path):
    items = [
        item("skill:opt", False, FAIL, "x"),
        item("skill:req", True, FAIL, "y"),
    ]
    actions = next_actions(items, tmp_path, "BLOCKED")
    assert actions[0].startswith("Fix skill:req")
    ready = next_actions([item("codex-mcp:s", False, UNVERIFIED, "z")], tmp_path, "READY")
    assert ready[1].startswith(f"Trust {tmp_path} in Codex")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_mcpcheck.py tests/test_report.py -v`
Expected: collection error (`kit.mcpcheck` does not exist yet, and conftest imports it). That is the expected red state; Step 4 creates the module.

- [ ] **Step 4: Create `kit/mcpcheck.py`**

```python
"""MCP smoke test over stdio (initialize -> tools/list) and Codex's own view of the server."""

from __future__ import annotations

import json
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path

from . import tools
from .mcpconfig import select_servers
from .model import FAIL, PASS, SKIPPED, UNVERIFIED, ItemResult
from .preflight import EnvReport

PROTOCOL_VERSION = "2025-06-18"
HANDSHAKE_TIMEOUT = 120.0  # first start downloads the package through npx


def find_command(name: str) -> str | None:
    return shutil.which(name)


def _stop(proc: subprocess.Popen) -> None:
    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def handshake(command: list[str], timeout: float = HANDSHAKE_TIMEOUT) -> tuple[str, str]:
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return FAIL, f"cannot start server: {exc}"
    lines: queue.Queue = queue.Queue()

    def pump() -> None:
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()
    deadline = time.monotonic() + timeout

    def send(message: dict) -> None:
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    def reply(request_id: int) -> dict:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            line = lines.get(timeout=remaining)
            if line is None:
                raise EOFError
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == request_id:
                return message

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "hackathon-kit", "version": "1"},
                },
            }
        )
        if "error" in reply(1):
            return FAIL, "initialize was rejected"
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        result = reply(2).get("result")
    except (TimeoutError, queue.Empty):
        return FAIL, f"no response within {timeout:.0f}s"
    except (EOFError, OSError):
        return FAIL, "server exited before answering"
    finally:
        _stop(proc)
    listed = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(listed, list) or not listed:
        return FAIL, "server listed no tools"
    names = ", ".join(str(t.get("name", "?")) for t in listed[:3] if isinstance(t, dict))
    return PASS, f"{len(listed)} tool(s): {names}"


def codex_lists(codex_path: str, target: Path, name: str, runner=None) -> bool | None:
    """True/False when `codex mcp list --json` answered; None when it could not be read."""
    runner = runner or tools.run_command
    code, output = runner([codex_path, "mcp", "list", "--json"], 60.0, target)
    if code != 0 or "[" not in output:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(output[output.index("[") :])
    except ValueError:
        return None
    if not isinstance(data, list):
        return None
    return any(isinstance(e, dict) and e.get("name") == name for e in data)


def _codex_item(name: str, env: EnvReport, target: Path) -> ItemResult:
    label = f"codex-mcp:{name}"
    codex = env.tools.get("codex")
    if codex is None or not codex.ok or not codex.path:
        return ItemResult(label, False, True, False, UNVERIFIED, "codex not found; check /mcp in Codex")
    if codex_lists(codex.path, target, name):
        return ItemResult(label, False, True, True, PASS, "listed by `codex mcp list`")
    detail = "not listed by `codex mcp list`; trust this project in Codex, then check /mcp"
    return ItemResult(label, False, True, False, UNVERIFIED, detail)


def check_servers(
    kit_root: Path, names: list[str], env: EnvReport, target: Path, offline: bool, no_mcp: bool
) -> list[ItemResult]:
    items = []
    for name, entry in select_servers(kit_root, names):
        label = f"mcp:{name}"
        if no_mcp:
            items.append(ItemResult(label, False, False, False, SKIPPED, "--no-mcp"))
            continue
        if offline:
            detail = "offline: npx would download the package"
            items.append(ItemResult(label, False, False, False, SKIPPED, detail))
            continue
        exe = find_command(entry["command"])
        if exe is None:
            detail = f"{entry['command']} not found; install Node.js or use --no-mcp"
            items.append(ItemResult(label, False, False, False, FAIL, detail))
            continue
        verdict, detail = handshake([exe, *entry["args"]])
        items.append(ItemResult(label, False, True, True, verdict, detail))
        items.append(_codex_item(name, env, target))
    return items
```

`check_servers` must call `find_command`, `handshake` and `codex_lists` through module globals (as written) so the conftest fakes apply.

- [ ] **Step 5: Update `kit/report.py`**

Replace `next_actions` with:

```python
def next_actions(items: list[ItemResult], target: Path, status: str) -> list[str]:
    actions = []
    for i in sorted(items, key=lambda i: not i.required):
        if i.verified == CONFLICT:
            actions.append(
                f"Resolve conflict in {i.name}: {i.detail}. Compare with the kit copy, then re-run."
            )
        elif i.verified == FAIL:
            actions.append(f"Fix {i.name}: {i.detail}. Then re-run.")
    if status != "BLOCKED":
        actions.append(f"Open Codex in {target} and run /skills to confirm the kit skills load.")
        if any(i.name.startswith("codex-mcp:") and i.verified == UNVERIFIED for i in items):
            actions.append(f"Trust {target} in Codex, then run /mcp to confirm the MCP server loads.")
    return actions[:3]
```

(import `UNVERIFIED` from `.model`; `sorted` is stable, so order within required/optional is kept.)

In `render`, replace the `mcp = ...` line with:

```python
    mcp_items = [i for i in items if i.name.startswith("mcp:")]
    if opts.no_mcp:
        mcp = "disabled (--no-mcp)"
    elif mcp_items:
        mcp = ", ".join(f"{i.name[4:]} {i.verified}" for i in mcp_items)
    else:
        mcp = f"none in profile '{opts.profile}'"
```

- [ ] **Step 6: Wire into `kit/app.py`**

Add `from . import mcpcheck`. After the web check:

```python
    if profile.mcp:
        items.extend(
            mcpcheck.check_servers(
                kit_root, profile.mcp, env, opts.target, opts.offline, opts.no_mcp
            )
        )
```

Change `_network_line(opts, actions)` to `_network_line(opts, actions, profile)`:

```python
def _network_line(opts: Options, actions, profile) -> str:
    if opts.offline:
        return "not used (--offline)"
    used = tools.network_used(actions)
    if profile.mcp and not opts.no_mcp:
        used.append("npx (MCP handshake)")
    return "used: " + "; ".join(used) if used else "not used"
```

In `_dry_run_text`, add `"npx (MCP handshake)"` to `planned` when `profile.mcp and not opts.no_mcp`, and after the tools block:

```python
    if profile.mcp:
        reason = "--no-mcp" if opts.no_mcp else ("--offline" if opts.offline else None)
        lines.append("Planned MCP checks:")
        for name in profile.mcp:
            lines.append(
                f"  SKIPPED   mcp:{name}  ({reason})"
                if reason
                else f"  HANDSHAKE mcp:{name}  (npx -y <pinned package>) [network]"
            )
```

(When `--offline` the network line already says `none (--offline)`; keep that branch first.)

- [ ] **Step 7: Run tests and lint**

Run: `uv run pytest -q ; uv run ruff check . ; uv run ruff format --check .`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add kit/mcpcheck.py kit/app.py kit/report.py tests/conftest.py tests/test_mcpcheck.py tests/test_report.py pyproject.toml
git commit -m "feat: smoke-test MCP servers over stdio and check codex listing"
```

---

### Task 8: Docs and example logs

**Files:**
- Create: `devtools/make_examples.py`, `docs/examples/{install,rerun,failure,offline,conflict}.log`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/COMPATIBILITY.md`, `docs/RULES_CHECKLIST.md`, `docs/TROUBLESHOOTING.md`
- Modify: `README.md`, `docs/ASSUMPTIONS.md`, `docs/TEST_REPORT.md`

**Interfaces:**
- Consumes: `kit.app.run(argv, cwd, out=...)`.
- Produces: example logs with `<target>` and `<home>` placeholders (no local paths).

- [ ] **Step 1: Create `devtools/make_examples.py`**

```python
"""Regenerate docs/examples/*.log from real kit runs in temporary workspaces. No network."""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kit.app import run  # noqa: E402

OUT = ROOT / "docs" / "examples"


def _run(target: Path, *argv: str) -> str:
    out = io.StringIO()
    code = run(["--target", str(target), *argv], cwd=target, out=out)
    text = out.getvalue()
    for path in {str(target), str(target.resolve())}:
        text = text.replace(path, "<target>")
    text = text.replace(str(Path.home()), "<home>")
    return f"$ bootstrap {' '.join(argv)}\n{text}(exit {code})\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for name in ("install", "rerun", "failure", "offline", "conflict"):
            (base / name).mkdir()
        logs = {
            "install": _run(base / "install"),
        }
        _run(base / "rerun")
        logs["rerun"] = _run(base / "rerun", "--verbose")
        (base / "failure" / "AGENTS.md").write_text(
            "<!-- hackathon-kit:begin -->\n<!-- hackathon-kit:begin -->\n", encoding="utf-8"
        )
        logs["failure"] = _run(base / "failure")
        logs["offline"] = _run(base / "offline", "--profile", "python", "--offline")
        _run(base / "conflict")
        skill = base / "conflict" / ".agents" / "skills" / "benchmark" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nmy note\n", encoding="utf-8")
        logs["conflict"] = _run(base / "conflict")
    for name, text in logs.items():
        (OUT / f"{name}.log").write_bytes(text.encode("utf-8"))
        print(f"wrote docs/examples/{name}.log")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate and inspect the logs**

Run: `uv run python devtools/make_examples.py`
Expected: five files. Open each and confirm: `install` → `Status:       READY` exit 0; `rerun` → READY, no CREATE; `failure` → `BLOCKED` exit 2; `offline` → `Network:      not used (--offline)`, MCP SKIPPED; `conflict` → CONFLICT on `skill:benchmark`, `PARTIAL` exit 1. `grep -n "Users\|home/" docs/examples/*.log` must find nothing except `<home>`/`<target>`. If an expectation is wrong, stop and report it (do not hand-edit logs).

- [ ] **Step 3: Write the docs (Korean)**

Each doc is short (40–120 lines) and states only facts from the code, the design spec (`docs/superpowers/specs/2026-10-28-hackathon-agent-kit-design.md`) and `mcp/manifest.json`. Required content:

- `docs/ARCHITECTURE.md`: why `kit/` instead of the instruction's `scripts/*.py` (import/test simplicity; `scripts/install.py` → `kit/tools.py`, `scripts/audit.py` → `kit/audit.py`); the pipeline `bootstrap.* → run_kit.py → kit.app.run`: preflight → plan (`plan.py`) → apply (`register.py`) → tools (`tools.py`) → verify (`verify.py`, `mcpconfig.verify_config`) → audit → web check → MCP check → report/log; module table (one line each for every `kit/*.py`); state/idempotency rules (spec §3.2); the two marker pairs; exit codes.
- `docs/SECURITY.md`: what is enforced (writes confined by `safe_path`, backups before change, no global config writes, allowlist/manifest, forbidden keys/env patterns, remote endpoint detection, masked local logs, repo scan test, offline means no network); the network actions that can happen and when (`uv tool install`, `pip install --user`, `npx -y` handshake); that `npx` resolves transitive dependencies by range (only the top package is pinned); that `uv tool`/`pip --user` install into user-level tool folders outside the target; that these checks reduce risk and are not a complete security boundary; that disabled servers (fetch/git/filesystem) and reasons come from the manifest.
- `docs/COMPATIBILITY.md`: Python 3.9+ (TOML parse and config audit need 3.11+, otherwise UNVERIFIED); bash 3.2+, Windows PowerShell 5.1+; Git Bash vs WSL `bash` on Windows; Node/npx needed only for MCP; why `2026.8.31` (2.0.0 needs node >=24); tested codex-cli 0.165.0 and the `codex mcp list --json` shape; Codex loads project `.codex/config.toml` only for trusted projects; shell-only mode limits (link to README).
- `docs/RULES_CHECKLIST.md`: the 7-item **사전 체험 15분 체크리스트** from spec §12, each with "안 되면 → 대체 경로"; a rules section restating spec §13 (no push/sync/release from the exam, no global config, no external model/API, no Computer Use or browser/proctoring manipulation, no written-answer automation, no real exam content, no `curl | bash`); explicitly no item that detects or tests proctoring/security features.
- `docs/TROUBLESHOOTING.md`: one entry per real message the kit prints — `CONFLICT` on AGENTS.md / skill files / `mcp-config` (what to compare, how to re-run), `security audit` FAIL, `tool:* install failed`, `not on PATH`, `npx not found`, `no response within 120s`, `codex-mcp` UNVERIFIED (trust the project), exit 64/65, shell-only PARTIAL, `TOML parse check needs Python 3.11+`. Use the exact message text from the code.
- `README.md`: add a profiles table (core/python/data/web/full exactly as Task 1 descriptions), the MCP section (what is registered, trust note, `--no-mcp`), update the options/network description for tool installs, state that shell-only mode (no Python) installs only AGENTS.md and skills for every profile (no tools, no MCP), and link the new docs and `docs/examples/`.
- `docs/ASSUMPTIONS.md`: add the MCP version choice and the unverified license line from the manifest, the unverified real-npx handshake, and that exam machines may lack Node.
- `docs/TEST_REPORT.md`: add a "계획 2" section with the actual `uv run pytest -q` counts, ruff results, the example-log generation, and an UNVERIFIED row: "실제 npx로 sequential-thinking 핸드셰이크 — `bootstrap.ps1 --profile python --target <빈 폴더>`로 사용자가 확인".

- [ ] **Step 4: Run tests and lint**

Run: `uv run pytest -q ; uv run ruff check . ; uv run ruff format --check .`
Expected: all pass (`devtools/` is linted; `docs/` is excluded).

- [ ] **Step 5: Commit**

```bash
git add devtools/make_examples.py docs/examples docs/ARCHITECTURE.md docs/SECURITY.md docs/COMPATIBILITY.md docs/RULES_CHECKLIST.md docs/TROUBLESHOOTING.md README.md docs/ASSUMPTIONS.md docs/TEST_REPORT.md
git commit -m "docs: add architecture, security, compatibility, checklist and example logs"
```
