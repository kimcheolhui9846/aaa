"""Audit the target's MCP config against mcp/allowlist.json. Reduces risk; not a guarantee."""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

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
    name = PureWindowsPath(str(command)).name.lower()
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


_TABLE = re.compile(r"^[ 	]*\[")
_MCP_TABLE = re.compile(r"^[ 	]*\[[ 	]*mcp_servers[ 	]*[.\]]")
_WORD = re.compile(r"[A-Za-z0-9_]+")
SCAN_NOTE = " (line scan; Python 3.11+ gives a full audit)"


def scan_lines(text: str, allowlist: dict) -> list[str]:
    """Conservative audit of raw text for when TOML cannot be parsed."""
    keys = [re.compile(rf"^[ 	]*({re.escape(k)})[ 	]*=") for k in allowlist["forbidden_keys"]]
    patterns = [re.compile(p) for p in allowlist["forbidden_env_patterns"]]
    problems: list[str] = []

    def add(problem: str) -> None:
        if problem not in problems:
            problems.append(problem)

    in_mcp = False
    for line in text.splitlines():
        if _TABLE.match(line):
            in_mcp = bool(_MCP_TABLE.match(line))
            header = mcpconfig._HEADER.match(line)
            if header and header.group(1) not in allowlist["servers"]:
                add(f"{header.group(1)}: not in mcp/allowlist.json")
        for key in keys:
            found = key.match(line)
            if found:
                add(f"forbidden key '{found.group(1)}' (remote transport)")
        if not in_mcp:
            continue
        if _REMOTE.search(line):
            add("remote endpoint in mcp_servers")
        for word in _WORD.findall(line):
            if any(p.search(word) for p in patterns):
                add(f"secret-like env '{word}'")
    return problems


def _fail(problems: list[str], suffix: str = "") -> ItemResult:
    more = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
    return ItemResult(LABEL, True, True, True, FAIL, "; ".join(problems[:3]) + more + suffix)


def audit_target(target: Path, kit_root: Path) -> ItemResult:
    path = target / mcpconfig.CONFIG_REL
    if not path.is_file():
        return ItemResult(LABEL, True, True, True, PASS, f"no {mcpconfig.CONFIG_REL}")
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return ItemResult(LABEL, True, True, False, FAIL, f"cannot read config: {exc}")
    status, data, error = mcpconfig.parse_toml(text)
    allowlist = mcpconfig.load_allowlist(kit_root)
    if status is None or status is False:
        problems = scan_lines(text, allowlist)
        if problems:
            return _fail(problems, SCAN_NOTE)
        if status is None:
            detail = "config audit needs Python 3.11+ (tomllib)"
        else:
            detail = f"cannot audit: config is not valid TOML ({error})"
        return ItemResult(LABEL, True, True, False, UNVERIFIED, detail)
    problems = audit_config(data, allowlist)
    if problems:
        return _fail(problems)
    return ItemResult(LABEL, True, True, True, PASS, "MCP config matches the allowlist")
