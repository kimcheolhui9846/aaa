from kit.fsops import State, sha256
from kit.model import Outcome
from kit.plan import FileChange, format_plan, plan_changes, plan_file
from kit.profiles import load_profile

REL = ".agents/skills/task-router/SKILL.md"


def test_fresh_workspace_plans_creates(kit_root, workspace):
    changes = plan_changes(workspace, kit_root, load_profile(kit_root, "core"), State())
    assert changes[0].rel == "AGENTS.md"
    assert all(c.outcome == Outcome.CREATE for c in changes)
    assert REL in {c.rel for c in changes}
    owners = {c.owner for c in changes}
    assert "skill:benchmark" in owners and "AGENTS.md" in owners


def test_identical_file_is_unchanged_and_recorded(kit_root, workspace):
    data = (kit_root / REL).read_bytes()
    (workspace / REL).parent.mkdir(parents=True)
    (workspace / REL).write_bytes(data)
    change = plan_file(workspace, REL, "skill:task-router", data, State())
    assert change.outcome == Outcome.UNCHANGED
    assert change.data is None and change.record == sha256(data)


def test_kit_written_file_is_updated(workspace):
    (workspace / "f.txt").write_bytes(b"old")
    change = plan_file(workspace, "f.txt", "o", b"new", State({"f.txt": sha256(b"old")}))
    assert change.outcome == Outcome.UPDATE and change.data == b"new"


def test_user_modified_file_conflicts(workspace):
    (workspace / "f.txt").write_bytes(b"user edit")
    change = plan_file(workspace, "f.txt", "o", b"new", State({"f.txt": sha256(b"old")}))
    assert change.outcome == Outcome.CONFLICT and change.record is None


def test_unrecorded_different_file_conflicts(workspace):
    (workspace / "f.txt").write_bytes(b"someone else's")
    assert plan_file(workspace, "f.txt", "o", b"new", State()).outcome == Outcome.CONFLICT


def test_directory_in_place_of_file_conflicts(workspace):
    (workspace / "f.txt").mkdir()
    assert plan_file(workspace, "f.txt", "o", b"new", State()).outcome == Outcome.CONFLICT


def test_escaping_path_conflicts(workspace):
    change = plan_file(workspace, "../evil.txt", "o", b"x", State())
    assert change.outcome == Outcome.CONFLICT and "outside" in change.detail


def test_existing_agents_md_is_appended(kit_root, workspace):
    (workspace / "AGENTS.md").write_text("# Mine\n", encoding="utf-8")
    changes = plan_changes(workspace, kit_root, load_profile(kit_root, "core"), State())
    assert changes[0].outcome == Outcome.APPEND


def test_non_utf8_agents_md_conflicts(kit_root, workspace):
    (workspace / "AGENTS.md").write_bytes(b"\xff\xfe\x00bad")
    changes = plan_changes(workspace, kit_root, load_profile(kit_root, "core"), State())
    assert changes[0].outcome == Outcome.CONFLICT and "UTF-8" in changes[0].detail


def test_format_plan_hides_unchanged_unless_verbose():
    changes = [FileChange("a", "o", Outcome.CREATE), FileChange("b", "o", Outcome.UNCHANGED)]
    short = format_plan(changes)
    assert "CREATE" in short and "  UNCHANGED" not in short
    assert short.splitlines()[-1] == (
        "Summary:      1 create, 0 update, 0 append, 0 conflict, 1 unchanged"
    )
    assert "UNCHANGED b" in format_plan(changes, verbose=True)
