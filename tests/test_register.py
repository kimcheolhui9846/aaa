import os

import pytest

from kit.fsops import State, sha256
from kit.model import Outcome
from kit.plan import FileChange
from kit.register import apply_changes


def test_apply_creates_files_and_records_state(workspace):
    change = FileChange("a/b.txt", "o", Outcome.CREATE, b"hi\n", sha256(b"hi\n"))
    apply_changes(workspace, [change], State(), "s1", "core")
    assert (workspace / "a" / "b.txt").read_bytes() == b"hi\n"
    assert State.load(workspace).files == {"a/b.txt": sha256(b"hi\n")}


def test_apply_backs_up_before_update(workspace):
    (workspace / "a.txt").write_bytes(b"old")
    change = FileChange("a.txt", "o", Outcome.UPDATE, b"new", sha256(b"new"))
    backups = apply_changes(workspace, [change], State(), "s1", "core")
    assert (workspace / "a.txt").read_bytes() == b"new"
    assert [b.read_bytes() for b in backups] == [b"old"]


def test_apply_leaves_conflicts_alone(workspace):
    (workspace / "a.txt").write_bytes(b"user")
    apply_changes(workspace, [FileChange("a.txt", "o", Outcome.CONFLICT)], State(), "s1", "core")
    assert (workspace / "a.txt").read_bytes() == b"user"
    assert State.load(workspace).files == {}


def test_apply_records_unchanged_without_writing(workspace):
    (workspace / "a.txt").write_bytes(b"same")
    change = FileChange("a.txt", "o", Outcome.UNCHANGED, None, sha256(b"same"))
    apply_changes(workspace, [change], State(), "s1", "core")
    assert State.load(workspace).files == {"a.txt": sha256(b"same")}
    assert not (workspace / ".kit" / "backups").exists()


def test_apply_cleans_temp_file_and_saves_state_on_failure(workspace, monkeypatch):
    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    change = FileChange("a.txt", "o", Outcome.CREATE, b"x", sha256(b"x"))
    with pytest.raises(OSError, match="disk full"):
        apply_changes(workspace, [change], State(), "s1", "core")
    assert not list(workspace.rglob("*.kit-tmp"))
    assert (workspace / ".kit" / "state.json").is_file()
