import sys

import pytest

from kit import preflight, tools
from kit.model import FAIL, PASS, SKIPPED, UNVERIFIED
from kit.preflight import EnvReport, ToolInfo
from kit.profiles import Profile
from kit.tools import plan_tools, run_tools

PYTEST = {
    "name": "pytest",
    "kind": "python-tool",
    "package": "pytest",
    "version": "8.4.2",
    "command": "pytest",
}


def env(uv=True):
    tool_map = {"uv": ToolInfo("uv", "/fake/uv", "uv 1") if uv else ToolInfo("uv")}
    return EnvReport("os", "arch", "sh", "3.12", True, tool_map)


def profile(*specs, report_only=False):
    return Profile("p", "", tools=list(specs), report_only=report_only)


@pytest.fixture
def probe(monkeypatch):
    """Make pytest missing until `installed` is set."""
    state = {"installed": False}

    def fake(name, timeout=15.0):
        return ToolInfo(name, f"/fake/{name}", "9.9") if state["installed"] else ToolInfo(name)

    monkeypatch.setattr(preflight, "probe_tool", fake)
    return state


class Runner:
    def __init__(self, results, probe_state=None):
        self.results = list(results)
        self.calls = []
        self.probe_state = probe_state

    def __call__(self, cmd, timeout=600.0, cwd=None):
        self.calls.append(cmd)
        code, out = self.results.pop(0)
        if code == 0 and self.probe_state is not None:
            self.probe_state["installed"] = True
        return code, out


def test_present_tool_passes_without_running(probe):
    probe["installed"] = True
    runner = Runner([])
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert item.name == "tool:pytest" and item.verified == PASS and runner.calls == []


def test_install_with_uv(probe):
    runner = Runner([(0, "ok")], probe)
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert runner.calls == [["/fake/uv", "tool", "install", "pytest==8.4.2"]]
    assert item.verified == PASS and "uv tool install pytest==8.4.2" in item.detail


def test_uv_retried_once_then_pip(probe):
    runner = Runner([(1, "boom"), (1, "boom"), (0, "ok")], probe)
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    pip = [sys.executable, "-m", "pip", "install", "--user", "pytest==8.4.2"]
    assert runner.calls[2] == pip and len(runner.calls) == 3
    assert item.verified == PASS


def test_all_attempts_fail(probe):
    runner = Runner([(1, "a"), (1, "b"), (1, "c"), (1, "network down\n")])
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert len(runner.calls) == 4
    assert item.verified == FAIL and item.detail == "install failed: network down"


def test_installed_but_not_on_path_is_unverified(probe):
    runner = Runner([(0, "ok")])  # probe never flips
    [item] = run_tools(plan_tools(profile(PYTEST), env(), False, False), runner)
    assert item.verified == UNVERIFIED and "not on PATH" in item.detail


def test_without_uv_only_pip(probe):
    [action] = plan_tools(profile(PYTEST), env(uv=False), False, False)
    assert [c[1:3] for c in action.commands] == [["-m", "pip"]]


@pytest.mark.parametrize(
    "offline, verify_only, report_only, verdict, fragment",
    [
        (True, False, False, SKIPPED, "offline"),
        (False, True, False, FAIL, "--verify-only"),
        (False, False, True, SKIPPED, "would run"),
    ],
)
def test_no_install_modes(probe, offline, verify_only, report_only, verdict, fragment):
    runner = Runner([])
    actions = plan_tools(profile(PYTEST, report_only=report_only), env(), offline, verify_only)
    [item] = run_tools(actions, runner)
    assert runner.calls == [] and item.verified == verdict and fragment in item.detail


def test_python_lib_is_advice_only():
    present = {"name": "json", "kind": "python-lib", "package": "json"}
    missing = {"name": "nope", "kind": "python-lib", "package": "kit_no_such_package_xyz"}
    a, b = run_tools(plan_tools(profile(present, missing), env(), False, False), Runner([]))
    assert a.verified == PASS
    assert b.verified == SKIPPED and "pip install --user kit_no_such_package_xyz" in b.detail


def test_node_project_is_not_a_tool_action():
    assert plan_tools(profile({"name": "n", "kind": "node-project"}), env(), False, False) == []


def test_network_used_lists_planned_installs(probe):
    actions = plan_tools(profile(PYTEST), env(), False, False)
    assert tools.network_used(actions) == ["uv tool install pytest==8.4.2"]
    assert "INSTALL" in tools.format_tool_plan(actions)


def test_python_profile_end_to_end_reports_network_not_used(run_kit):
    code, out = run_kit("--profile", "python", "--no-mcp")
    assert code == 0, out
    assert "Network:      not used" in out


def test_dry_run_shows_install_and_runs_nothing(run_kit, workspace, probe, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("dry-run must not run commands")

    monkeypatch.setattr(tools, "run_command", forbidden)
    code, out = run_kit("--profile", "python", "--dry-run")
    assert code == 0
    assert "INSTALL   tool:pytest" in out
    assert "Network:      would use:" in out and "pytest==8.4.2" in out
    assert list(workspace.iterdir()) == []
