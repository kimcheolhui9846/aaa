import json

import pytest

from kit.model import UsageError
from kit.profiles import available_profiles, load_profile

ALL_SKILLS = [
    "task-router",
    "tdd-automator",
    "algorithm-optimizer",
    "submission-validator",
    "implementation-review",
    "benchmark",
]


def _write(root, name, data):
    folder = root / "profiles"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def test_core_profile(kit_root):
    profile = load_profile(kit_root, "core")
    assert profile.skills == ALL_SKILLS
    assert profile.required_skills == ALL_SKILLS[:4]
    assert profile.tools == [] and profile.mcp == []


def test_extends_merges_lists_base_first(tmp_path):
    _write(
        tmp_path,
        "base",
        {"name": "base", "description": "b", "skills": ["a", "b"], "tools": [{"name": "pytest"}]},
    )
    _write(
        tmp_path,
        "child",
        {
            "name": "child",
            "description": "c",
            "extends": "base",
            "skills": ["b", "c"],
            "tools": [{"name": "ruff"}],
        },
    )
    profile = load_profile(tmp_path, "child")
    assert profile.skills == ["a", "b", "c"]
    assert profile.tools == [{"name": "pytest"}, {"name": "ruff"}]
    assert profile.description == "c"


def test_cycle_is_rejected(tmp_path):
    _write(tmp_path, "a", {"name": "a", "extends": "b"})
    _write(tmp_path, "b", {"name": "b", "extends": "a"})
    with pytest.raises(UsageError, match="cycle"):
        load_profile(tmp_path, "a")


def test_unknown_profile_lists_available(tmp_path):
    _write(tmp_path, "base", {"name": "base"})
    with pytest.raises(UsageError, match="available: base"):
        load_profile(tmp_path, "nope")


def test_available_profiles_sorted(tmp_path):
    _write(tmp_path, "web", {"name": "web"})
    _write(tmp_path, "core", {"name": "core"})
    assert available_profiles(tmp_path) == ["core", "web"]
