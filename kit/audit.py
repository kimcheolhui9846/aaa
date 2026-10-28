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
        detail = f"cannot audit: config is not valid TOML ({error})"
        return ItemResult(LABEL, True, True, False, UNVERIFIED, detail)
    problems = audit_config(data, mcpconfig.load_allowlist(kit_root))
    if problems:
        more = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
        return ItemResult(LABEL, True, True, True, FAIL, "; ".join(problems[:3]) + more)
    return ItemResult(LABEL, True, True, True, PASS, "MCP config matches the allowlist")
