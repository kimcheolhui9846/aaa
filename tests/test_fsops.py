import pytest

from kit.fsops import PathEscapeError, State, backup_file, safe_path, sha256


def test_safe_path_inside(tmp_path):
    assert safe_path(tmp_path, "a/b.txt") == (tmp_path / "a" / "b.txt").resolve()


@pytest.mark.parametrize("rel", ["../x", "a/../../x"])
def test_safe_path_rejects_parent_traversal(tmp_path, rel):
    with pytest.raises(PathEscapeError):
        safe_path(tmp_path, rel)


def test_safe_path_rejects_absolute_outside(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(PathEscapeError):
        safe_path(root, str(tmp_path / "elsewhere.txt"))


def test_safe_path_rejects_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not permitted on this system")
    with pytest.raises(PathEscapeError):
        safe_path(root, "link/x.txt")


def test_state_roundtrip(tmp_path):
    State({"a.txt": "1"}).save(tmp_path, "core")
    assert State.load(tmp_path).files == {"a.txt": "1"}


def test_state_save_is_deterministic(tmp_path):
    State({"b": "2", "a": "1"}).save(tmp_path, "core")
    first = (tmp_path / ".kit" / "state.json").read_bytes()
    State({"a": "1", "b": "2"}).save(tmp_path, "core")
    assert (tmp_path / ".kit" / "state.json").read_bytes() == first


def test_state_load_corrupt_returns_empty(tmp_path):
    (tmp_path / ".kit").mkdir()
    (tmp_path / ".kit" / "state.json").write_text("{", encoding="utf-8")
    assert State.load(tmp_path).files == {}


def test_backup_copies_into_stamp_dir(tmp_path):
    (tmp_path / "AGENTS.md").write_bytes(b"original")
    dst = backup_file(tmp_path, "AGENTS.md", "20261028-120000")
    assert dst == (tmp_path / ".kit/backups/20261028-120000/AGENTS.md").resolve()
    assert dst.read_bytes() == b"original"


def test_sha256_known_value():
    assert sha256(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
