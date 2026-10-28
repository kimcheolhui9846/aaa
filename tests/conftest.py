from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

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
