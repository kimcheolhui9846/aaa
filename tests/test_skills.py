import pytest

from kit.skills import MAX_DESCRIPTION, parse_frontmatter, validate_skill

CORE = ["task-router", "tdd-automator", "algorithm-optimizer", "submission-validator"]
WITH_LANGUAGES = ["tdd-automator", "algorithm-optimizer", "submission-validator"]


def _skill(root, name, frontmatter):
    folder = root / name
    folder.mkdir()
    (folder / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Body\n", encoding="utf-8")
    return folder


def test_parse_frontmatter_strips_quotes():
    text = '---\nname: x\ndescription: "a: b"\n---\nbody'
    assert parse_frontmatter(text) == {"name": "x", "description": "a: b"}


def test_parse_requires_opening_marker():
    with pytest.raises(ValueError, match="opening"):
        parse_frontmatter("name: x\n")


def test_parse_requires_closing_marker():
    with pytest.raises(ValueError, match="closing"):
        parse_frontmatter("---\nname: x\n")


def test_validate_reports_name_mismatch(tmp_path):
    folder = _skill(tmp_path, "real", 'name: other\ndescription: "Use when x. Do NOT use y."')
    assert any("does not match" in e for e in validate_skill(folder))


def test_validate_requires_do_not_use(tmp_path):
    folder = _skill(tmp_path, "s", 'name: s\ndescription: "Use when x."')
    assert any("Do NOT use" in e for e in validate_skill(folder))


def test_validate_limits_description(tmp_path):
    long = "Use when " + "x" * MAX_DESCRIPTION + " Do NOT use y."
    folder = _skill(tmp_path, "s", f'name: s\ndescription: "{long}"')
    assert any("too long" in e for e in validate_skill(folder))


def test_validate_missing_skill_md(tmp_path):
    (tmp_path / "empty").mkdir()
    assert validate_skill(tmp_path / "empty") == ["empty: SKILL.md missing"]


@pytest.mark.parametrize("name", CORE)
def test_core_skill_is_valid(kit_root, name):
    assert validate_skill(kit_root / ".agents" / "skills" / name) == []


@pytest.mark.parametrize("name", CORE)
def test_core_skill_description_is_one_quoted_line(kit_root, name):
    text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("description:"))
    assert line.startswith('description: "') and line.endswith('"')
    assert line.count('"') == 2


@pytest.mark.parametrize("name", CORE)
def test_core_skill_has_example(kit_root, name):
    assert list((kit_root / ".agents" / "skills" / name / "examples").glob("*.md"))


@pytest.mark.parametrize("name", WITH_LANGUAGES)
def test_language_reference_exists(kit_root, name):
    assert (kit_root / ".agents" / "skills" / name / "references" / "languages.md").is_file()


def test_agents_md_policy(kit_root):
    text = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    for heading in (
        "## Understand the task",
        "## Build",
        "## Validate",
        "## Optimize",
        "## Restrictions",
    ):
        assert heading in text
    assert "task-router" in text
    assert "hackathon-kit:begin" not in text
