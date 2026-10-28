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
