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
        detail = f"TOML parse check needs Python 3.11+; {TRUST_NOTE}"
        return ItemResult(label, False, True, True, UNVERIFIED, detail)
    if status is False:
        return ItemResult(label, False, True, True, FAIL, f"not valid TOML: {error}")
    return ItemResult(label, False, True, True, PASS, TRUST_NOTE)
