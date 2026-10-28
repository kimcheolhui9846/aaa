import shutil

from kit.fsops import State
from kit.model import CONFLICT, FAIL, PASS, Outcome
from kit.plan import FileChange, plan_changes
from kit.profiles import load_profile
from kit.register import apply_changes
from kit.verify import verify_target

REQUIRED = {
    "target writable",
    "AGENTS.md",
    "skill:task-router",
    "skill:tdd-automator",
    "skill:algorithm-optimizer",
    "skill:submission-validator",
}


def _install(kit_root, workspace):
    profile = load_profile(kit_root, "core")
    apply_changes(
        workspace, plan_changes(workspace, kit_root, profile, State()), State(), "s", "core"
    )
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
        "skill:task-router"
    ]
    assert item.verified == FAIL and "differ" in item.detail


def test_conflict_from_plan_is_reported(kit_root, workspace):
    profile = _install(kit_root, workspace)
    changes = [
        FileChange(
            ".agents/skills/task-router/SKILL.md",
            "skill:task-router",
            Outcome.CONFLICT,
            detail="edited by user",
        )
    ]
    item = _by_name(verify_target(workspace, kit_root, profile, changes, True, True))[
        "skill:task-router"
    ]
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
