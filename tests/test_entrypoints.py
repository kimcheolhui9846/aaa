import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kit.agentsmd import BEGIN

KIT_ROOT = Path(__file__).resolve().parent.parent
NO_PYTHON = "kit-no-such-python"


def _find_bash():
    if os.environ.get("KIT_TEST_BASH"):
        return os.environ["KIT_TEST_BASH"]
    if os.name == "nt":
        # C:\Windows\System32\bash.exe is WSL, which cannot see this Python; use Git Bash.
        git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git/bin/bash.exe"
        return str(git_bash) if git_bash.is_file() else None
    return shutil.which("bash")


def _find_powershell():
    return shutil.which("powershell") or shutil.which("pwsh")


BASH = _find_bash()
POWERSHELL = _find_powershell()
SHELLS = ["bash", "powershell"]


def _command(kind):
    if kind == "bash":
        if not BASH:
            pytest.skip("bash not found")
        return [BASH, (KIT_ROOT / "bootstrap.sh").as_posix()]
    if not POWERSHELL:
        pytest.skip("PowerShell not found")
    return [
        POWERSHELL,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(KIT_ROOT / "bootstrap.ps1"),
    ]


def _path(kind, path):
    return path.as_posix() if kind == "bash" else str(path)


def _python(kind):
    return Path(sys.executable).as_posix() if kind == "bash" else sys.executable


def _run(kind, *args, cwd, python):
    env = dict(os.environ, KIT_PYTHON=python)
    return subprocess.run(
        _command(kind) + list(args),
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


@pytest.mark.parametrize("kind", SHELLS)
def test_help_exits_zero(kind, workspace):
    proc = _run(kind, "--help", cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 0, proc.stderr
    assert "Usage" in proc.stdout and "Exit codes" in proc.stdout


@pytest.mark.parametrize("kind", SHELLS)
@pytest.mark.parametrize("with_python", [True, False])
def test_bad_argument_exits_64(kind, with_python, workspace):
    python = _python(kind) if with_python else NO_PYTHON
    assert _run(kind, "--bogus", cwd=workspace, python=python).returncode == 64


@pytest.mark.parametrize("kind", SHELLS)
@pytest.mark.parametrize("with_python", [True, False])
def test_missing_target_exits_65(kind, with_python, workspace):
    python = _python(kind) if with_python else NO_PYTHON
    missing = _path(kind, workspace / "missing")
    assert _run(kind, "--target", missing, cwd=workspace, python=python).returncode == 65


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_installs_then_skips(kind, workspace):
    first = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert first.returncode == 1, first.stdout + first.stderr
    assert "shell-only" in first.stdout and "Status:       PARTIAL" in first.stdout
    assert (workspace / "AGENTS.md").read_text(encoding="utf-8").startswith(BEGIN)
    assert len(list((workspace / ".agents" / "skills").iterdir())) == 6
    second = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert second.returncode == 1
    assert "SKIP" in second.stdout and "CONFLICT" not in second.stdout


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_conflicts_on_foreign_agents_md(kind, workspace):
    (workspace / "AGENTS.md").write_bytes(b"mine\n")
    proc = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 2, proc.stdout
    assert "Status:       BLOCKED" in proc.stdout
    assert (workspace / "AGENTS.md").read_bytes() == b"mine\n"


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_dry_run_writes_nothing(kind, workspace):
    proc = _run(kind, "--dry-run", cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 0, proc.stdout
    assert "DRY RUN" in proc.stdout
    assert list(workspace.iterdir()) == []


@pytest.mark.parametrize("kind", SHELLS)
def test_delegates_to_python(kind, workspace):
    proc = _run(kind, "--target", _path(kind, workspace), cwd=workspace, python=_python(kind))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Status:       READY" in proc.stdout
    assert f"shell={kind}" in proc.stdout


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_output_upgrades_cleanly_with_python(kind, workspace):
    _run(kind, cwd=workspace, python=NO_PYTHON)
    proc = _run(kind, cwd=workspace, python=_python(kind))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Status:       READY" in proc.stdout


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_write_failure_is_blocked(kind, workspace):
    (workspace / ".agents").write_bytes(b"not a directory\n")
    proc = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "Status:       BLOCKED" in proc.stdout
    assert (workspace / ".agents").read_bytes() == b"not a directory\n"
    assert not [p for p in workspace.rglob("*") if ".kit-tmp" in p.name]


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_refuses_kit_folder_as_target(kind, workspace):
    before = (KIT_ROOT / "AGENTS.md").read_bytes()
    for args in (["--target", _path(kind, KIT_ROOT)], []):
        cwd = workspace if args else KIT_ROOT
        proc = _run(kind, *args, cwd=cwd, python=NO_PYTHON)
        assert proc.returncode == 65, proc.stdout + proc.stderr
        assert "kit folder itself" in proc.stderr
    assert (KIT_ROOT / "AGENTS.md").read_bytes() == before


@pytest.mark.parametrize("kind", SHELLS)
@pytest.mark.parametrize("with_python", [True, False])
def test_empty_target_exits_64(kind, with_python, workspace):
    python = _python(kind) if with_python else NO_PYTHON
    assert _run(kind, "--target", "", cwd=workspace, python=python).returncode == 64


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_rejects_verify_only_and_writes_nothing(kind, workspace):
    proc = _run(kind, "--verify-only", cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 64, proc.stdout + proc.stderr
    assert "--verify-only requires Python 3.9+" in proc.stderr
    assert list(workspace.iterdir()) == []


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_unreadable_agents_md_is_conflict(kind, workspace):
    (workspace / "AGENTS.md").mkdir()
    proc = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "CONFLICT" in proc.stdout and "Status:       BLOCKED" in proc.stdout


@pytest.mark.parametrize("kind", SHELLS)
def test_fallback_clears_stale_tmp_copies(kind, workspace):
    stale = workspace / ".agents" / "skills" / "task-router.kit-tmp"
    stale.mkdir(parents=True)
    (stale / "old.txt").write_text("x", encoding="utf-8")
    (workspace / "AGENTS.md.kit-tmp").write_text("old", encoding="utf-8")
    proc = _run(kind, cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert not [p for p in workspace.rglob("*") if ".kit-tmp" in p.name]
    assert not (workspace / ".agents" / "skills" / "task-router" / "task-router").exists()
    assert (workspace / ".agents" / "skills" / "task-router" / "SKILL.md").is_file()
