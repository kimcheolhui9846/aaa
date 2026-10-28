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
    text = (
        '[mcp_servers.sequential-thinking]\ncommand = "x"\n\n'
        f'{BEGIN}\n[mcp_servers.sequential-thinking]\ncommand = "npx"\n{END}\n'
    )
    assert "outside the kit block" in check_merged(text, ["sequential-thinking"])


def test_check_merged_detects_invalid_toml():
    if parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    text = f'model = \n{BEGIN}\n[mcp_servers.s]\ncommand = "npx"\n{END}\n'
    assert "not be valid TOML" in check_merged(text, ["s"])


def test_check_merged_accepts_clean_merge():
    text = (
        'model = "m"\n[mcp_servers.other]\ncommand = "uvx"\n\n'
        f'{BEGIN}\n[mcp_servers.s]\ncommand = "npx"\n{END}\n'
    )
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
    old = f'{BEGIN}\n[mcp_servers.sequential-thinking]\ncommand = "old"\n{END}\n'
    _write_config(workspace, old)
    item = verify_config(workspace, kit_root, ["sequential-thinking"], None)
    assert item.verified == FAIL and "outdated" in item.detail


def test_verify_config_conflict(kit_root, workspace):
    item = verify_config(workspace, kit_root, ["sequential-thinking"], "already defined")
    assert item.verified == CONFLICT and item.required is False
