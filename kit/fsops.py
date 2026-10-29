"""Filesystem helpers: confined paths, hashing, kit state and backups."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

STATE_REL = ".kit/state.json"


class PathEscapeError(Exception):
    """A path resolved outside the target workspace."""


def safe_path(root: Path, rel: str) -> Path:
    """Resolve rel under root, refusing anything (.., absolute, symlink) that escapes it."""
    root = root.resolve()
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise PathEscapeError(f"refusing path outside target: {rel}")
    return candidate


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


class State:
    """Hashes of files the kit wrote, so re-runs can tell kit edits from user edits."""

    def __init__(self, files: dict[str, str] | None = None):
        self.files = dict(files or {})

    @classmethod
    def load(cls, target: Path) -> State:
        path = target / STATE_REL
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        files = data.get("files", {}) if isinstance(data, dict) else {}
        return cls(files if isinstance(files, dict) else {})

    def save(self, target: Path, profile: str) -> None:
        path = safe_path(target, STATE_REL)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "profile": profile, "files": dict(sorted(self.files.items()))}
        path.write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def backup_file(target: Path, rel: str, stamp: str) -> Path:
    src = safe_path(target, rel)
    dst = safe_path(target, f".kit/backups/{stamp}/{rel}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst
