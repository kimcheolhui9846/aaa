from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest

from kit import mcpcheck, preflight, tools
from kit.app import run
from kit.model import PASS
from kit.preflight import ToolInfo

KIT_ROOT = Path(__file__).resolve().parent.parent


def tree_digest(root: Path, exclude: tuple[str, ...] = (".kit/logs/",)) -> dict[str, str]:
    """Map every file under root (POSIX relative path) to its SHA-256."""
    digest = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith(exclude):
            digest[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


@pytest.fixture
def kit_root() -> Path:
    return KIT_ROOT


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch) -> Path:
    """Keep every test away from the real ~/.codex and ~/.agents."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


@pytest.fixture
def workspace(tmp_path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


@pytest.fixture(autouse=True)
def fast_preflight(request, monkeypatch):
    """Skip slow real tool probes unless the test is marked real_preflight."""
    if request.node.get_closest_marker("real_preflight"):
        return
    monkeypatch.setattr(
        preflight,
        "probe_tool",
        lambda name, timeout=15.0: ToolInfo(name, f"/fake/{name}", "fake 1.0"),
    )


@pytest.fixture(autouse=True)
def no_real_commands(monkeypatch):
    """Tool installs and codex calls never run for real in tests."""
    monkeypatch.setattr(
        tools,
        "run_command",
        lambda cmd, timeout=600.0, cwd=None: (1, "real commands are disabled in tests"),
    )


@pytest.fixture(autouse=True)
def fake_mcp(request, monkeypatch):
    """Never start npx or codex in tests unless marked real_mcp."""
    if request.node.get_closest_marker("real_mcp"):
        return
    monkeypatch.setattr(mcpcheck, "find_command", lambda name: f"/fake/{name}")
    monkeypatch.setattr(
        mcpcheck, "handshake", lambda command, timeout=120.0: (PASS, "1 tool(s): fake")
    )
    monkeypatch.setattr(mcpcheck, "codex_lists", lambda codex_path, target, name, runner=None: None)


@pytest.fixture
def run_kit(workspace):
    def _run(*argv: str, cwd: Path | None = None) -> tuple[int, str]:
        out = io.StringIO()
        code = run(list(argv), cwd=cwd or workspace, out=out)
        return code, out.getvalue()

    return _run
