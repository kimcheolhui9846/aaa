from kit.agentsmd import BEGIN
from kit.profiles import load_profile


def test_first_run_is_ready(run_kit, workspace, kit_root):
    code, out = run_kit()
    assert code == 0, out
    assert "Status:       READY" in out
    assert (workspace / "AGENTS.md").read_text(encoding="utf-8").startswith(BEGIN)
    expected = len(load_profile(kit_root, "core").skills)
    assert len(list((workspace / ".agents" / "skills").iterdir())) == expected


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
