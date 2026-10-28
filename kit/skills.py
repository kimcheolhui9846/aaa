"""Minimal SKILL.md frontmatter parsing and validation (no YAML dependency)."""

from __future__ import annotations

from pathlib import Path

MAX_DESCRIPTION = 400


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat `key: value` block between the leading `---` lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---'")
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {line!r}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    raise ValueError("missing closing '---'")


def validate_skill(skill_dir: Path) -> list[str]:
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{name}: SKILL.md missing"]
    try:
        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return [f"{name}: {exc}"]
    errors = []
    if meta.get("name") != name:
        errors.append(f"{name}: frontmatter name '{meta.get('name')}' does not match folder")
    description = meta.get("description", "")
    if not description:
        errors.append(f"{name}: description missing")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"{name}: description too long ({len(description)} > {MAX_DESCRIPTION})")
    elif "Do NOT use" not in description:
        errors.append(f"{name}: description must say when 'Do NOT use' the skill")
    return errors
