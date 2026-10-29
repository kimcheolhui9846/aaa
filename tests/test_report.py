from kit.cli import Options
from kit.model import CONFLICT, FAIL, PASS, UNVERIFIED, ItemResult
from kit.preflight import EnvReport, ToolInfo
from kit.report import next_actions, overall_status, render


def item(name, required, verified, detail=""):
    return ItemResult(name, required, True, True, verified, detail)


def test_all_pass_is_ready():
    assert overall_status([item("a", True, PASS), item("b", False, PASS)]) == ("READY", 0)


def test_unverified_does_not_block():
    assert overall_status([item("a", True, UNVERIFIED)]) == ("READY", 0)


def test_optional_failure_is_partial():
    assert overall_status([item("a", True, PASS), item("b", False, FAIL)]) == ("PARTIAL", 1)


def test_optional_conflict_is_partial():
    assert overall_status([item("a", True, PASS), item("b", False, CONFLICT)]) == ("PARTIAL", 1)


def test_required_failure_is_blocked():
    assert overall_status([item("a", True, FAIL), item("b", False, PASS)]) == ("BLOCKED", 2)


def test_required_conflict_is_blocked():
    assert overall_status([item("a", True, CONFLICT)]) == ("BLOCKED", 2)


def test_shell_fallback_is_partial():
    assert overall_status([item("a", True, PASS)], shell_fallback=True) == ("PARTIAL", 1)


def test_next_actions_ready_points_to_skills_check(tmp_path):
    actions = next_actions([item("a", True, PASS)], tmp_path, "READY")
    assert actions == [f"Open Codex in {tmp_path} and run /skills to confirm the kit skills load."]


def test_next_actions_capped_at_three(tmp_path):
    items = [item(f"skill:{n}", True, FAIL, "not installed") for n in "abcd"]
    actions = next_actions(items, tmp_path, "BLOCKED")
    assert len(actions) == 3 and actions[0].startswith("Fix skill:a")


def test_render_contains_report_fields(tmp_path):
    env = EnvReport(
        "Linux 6",
        "x86_64",
        "bash",
        "3.12.0",
        True,
        {"git": ToolInfo("git", "/usr/bin/git", "git 2.0"), "uv": ToolInfo("uv")},
    )
    opts = Options("core", tmp_path, False, False, False, False, False)
    items = [
        item("AGENTS.md", True, PASS),
        item("skill:x", True, PASS),
        item("skill:y", False, FAIL, "not installed"),
    ]
    text = render(env, opts, items, "PARTIAL", ["do this"])
    assert "Tools:        git OK, uv missing" in text
    assert "AGENTS.md:    INSTALLED" in text
    assert "Skills:       2 expected / 1 verified" in text
    assert "Codex load:   UNVERIFIED (open Codex and run /skills)" in text
    assert "  FAIL       optional skill:y  (not installed)" in text
    assert "Status:       PARTIAL" in text
    assert text.rstrip().endswith("  - do this")


def test_next_actions_required_first_and_trust(tmp_path):
    items = [
        item("skill:opt", False, FAIL, "x"),
        item("skill:req", True, FAIL, "y"),
    ]
    actions = next_actions(items, tmp_path, "BLOCKED")
    assert actions[0].startswith("Fix skill:req")
    ready = next_actions([item("codex-mcp:s", False, UNVERIFIED, "z")], tmp_path, "READY")
    assert ready[1].startswith(f"Trust {tmp_path} in Codex")
