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


def test_posix_command_path_is_normalised():
    assert audit_config(_servers(command="/usr/bin/npx"), ALLOW) == []


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
    _write(workspace, 'model = "x"\n')
    monkeypatch.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))
    assert audit_target(workspace, kit_root).verified == UNVERIFIED


def test_remote_server_blocks_the_run(run_kit, workspace):
    if mcpconfig.parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    _write(workspace, '[mcp_servers.remote]\nurl = "https://example.invalid/mcp"\n')
    code, out = run_kit()
    assert code == 2 and "security audit" in out


def test_same_name_outside_block_with_disallowed_command_blocks(run_kit, workspace):
    if mcpconfig.parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    _write(workspace, '[mcp_servers.sequential-thinking]\ncommand = "node"\n')
    code, out = run_kit("--profile", "python")
    assert code == 2 and "security audit" in out


REMOTE = '[mcp_servers.remote]\nurl = "https://example.invalid/mcp"\n'


def _no_tomllib(monkeypatch):
    monkeypatch.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))


def test_line_scan_fails_remote_without_tomllib(kit_root, workspace, monkeypatch):
    _write(workspace, REMOTE)
    _no_tomllib(monkeypatch)
    item = audit_target(workspace, kit_root)
    assert item.verified == FAIL and item.required is True
    assert "remote: not in mcp/allowlist.json" in item.detail
    assert "line scan" in item.detail


def test_line_scan_remote_blocks_the_run(run_kit, workspace, monkeypatch):
    _write(workspace, REMOTE)
    _no_tomllib(monkeypatch)
    code, out = run_kit()
    assert code == 2 and "security audit" in out and "Status:       BLOCKED" in out


def test_line_scan_finds_secret_env_and_endpoint(kit_root, workspace, monkeypatch):
    _write(
        workspace,
        '[mcp_servers.sequential-thinking]\ncommand = "npx"\nargs = ["https://x.invalid"]\n'
        '[mcp_servers.sequential-thinking.env]\nOPENAI_API_KEY = "x"\n',
    )
    _no_tomllib(monkeypatch)
    item = audit_target(workspace, kit_root)
    assert item.verified == FAIL
    assert "remote endpoint in mcp_servers" in item.detail
    assert "secret-like env 'OPENAI_API_KEY'" in item.detail


def test_clean_config_without_tomllib_is_unverified_and_shown(run_kit, workspace, monkeypatch):
    _write(workspace, '# nothing here\nmodel = "x"\n')
    _no_tomllib(monkeypatch)
    code, out = run_kit()
    assert code == 0
    assert "UNVERIFIED required security audit" in out
    assert "Check security audit by hand: config audit needs Python 3.11+ (tomllib)." in out


def test_invalid_toml_with_remote_server_fails(kit_root, workspace):
    _write(workspace, REMOTE + "broken = = =\n")
    item = audit_target(workspace, kit_root)
    if mcpconfig.parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    assert item.verified == FAIL and "line scan" in item.detail


def test_invalid_toml_without_findings_stays_unverified(kit_root, workspace):
    if mcpconfig.parse_toml("")[0] is None:
        pytest.skip("tomllib needs Python 3.11+")
    _write(workspace, "broken = = =\n")
    assert audit_target(workspace, kit_root).verified == UNVERIFIED


def test_line_scan_ignores_url_outside_mcp_servers(kit_root, workspace, monkeypatch):
    kit = (
        f'{mcpconfig.BEGIN}\n[mcp_servers.sequential-thinking]\ncommand = "npx"\n'
        f'args = ["-y", "pkg@1"]\n{mcpconfig.END}\n'
    )
    _write(workspace, '[other]\nurl = "https://x"\n\n' + kit)
    _no_tomllib(monkeypatch)
    assert audit_target(workspace, kit_root).verified == UNVERIFIED
