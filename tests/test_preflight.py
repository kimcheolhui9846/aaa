import os
import platform

import pytest

from kit import preflight

pytestmark = pytest.mark.real_preflight


@pytest.fixture
def fake_tools(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if os.name == "nt":
        (bin_dir / "faketool.cmd").write_text("@echo fake-tool 9.9.9\r\n", encoding="ascii")
        (bin_dir / "brokentool.cmd").write_text("@exit /b 3\r\n", encoding="ascii")
    else:
        for name, body in (("faketool", "echo fake-tool 9.9.9"), ("brokentool", "exit 3")):
            script = bin_dir / name
            script.write_text(f"#!/bin/sh\n{body}\n", encoding="ascii")
            script.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return bin_dir


def test_probe_reports_first_version_line(fake_tools):
    info = preflight.probe_tool("faketool")
    assert info.ok
    assert info.version == "fake-tool 9.9.9"


def test_probe_missing_tool():
    info = preflight.probe_tool("definitely-not-a-tool-xyz")
    assert info.path is None
    assert not info.ok


def test_probe_failing_tool(fake_tools):
    info = preflight.probe_tool("brokentool")
    assert info.path is not None
    assert not info.ok


def test_run_preflight_reports_python_and_writable(workspace, monkeypatch):
    monkeypatch.setattr(preflight, "TOOLS", ())
    env = preflight.run_preflight(workspace)
    assert env.python == platform.python_version()
    assert env.tools["python"].ok
    assert env.target_writable


def test_shell_comes_from_entry_point(workspace, monkeypatch):
    monkeypatch.setattr(preflight, "TOOLS", ())
    monkeypatch.setenv("KIT_SHELL", "bash")
    assert preflight.run_preflight(workspace).shell == "bash"
