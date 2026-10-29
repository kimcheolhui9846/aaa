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
        out = {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": tools}}
        print(json.dumps(out), flush=True)
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
    pkg = "@modelcontextprotocol/server-sequential-thinking@2026.8.31"
    assert seen["command"][1:] == ["-y", pkg]
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
