"""Check what is actually in the target, item by item. Codex loading itself is not observable."""

from __future__ import annotations

from pathlib import Path

from .agentsmd import MarkerError, extract_block
from .model import CONFLICT, FAIL, PASS, ItemResult, Outcome
from .plan import FileChange, iter_skill_files
from .profiles import Profile
from .skills import validate_skill


def verify_target(
    target: Path,
    kit_root: Path,
    profile: Profile,
    changes: list[FileChange],
    check_writable: bool,
    writable: bool,
) -> list[ItemResult]:
    conflicts: dict[str, str] = {}
    for change in changes:
        if change.outcome == Outcome.CONFLICT:
            conflicts.setdefault(change.owner, f"{change.rel}: {change.detail}")

    items = []
    if check_writable:
        items.append(
            ItemResult(
                "target writable",
                True,
                True,
                True,
                PASS if writable else FAIL,
                "" if writable else f"cannot write to {target}",
            )
        )
    items.append(_verify_agents_md(target, kit_root, conflicts))
    for name in profile.skills:
        items.append(
            _verify_skill(target, kit_root, name, name in profile.required_skills, conflicts)
        )
    return items


def _verify_agents_md(target: Path, kit_root: Path, conflicts: dict[str, str]) -> ItemResult:
    name = "AGENTS.md"
    if name in conflicts:
        return ItemResult(name, True, True, False, CONFLICT, conflicts[name])
    path = target / name
    if not path.is_file():
        return ItemResult(name, True, False, False, FAIL, "AGENTS.md missing")
    try:
        found = extract_block(path.read_bytes().decode("utf-8"))
    except (MarkerError, UnicodeDecodeError) as exc:
        return ItemResult(name, True, True, False, FAIL, str(exc))
    if found is None:
        return ItemResult(name, True, True, False, FAIL, "kit block missing")
    body = (kit_root / name).read_text(encoding="utf-8").strip()
    if found[2] != body:
        return ItemResult(name, True, True, True, FAIL, "kit block is outdated")
    return ItemResult(name, True, True, True, PASS)


def _verify_skill(
    target: Path, kit_root: Path, name: str, required: bool, conflicts: dict[str, str]
) -> ItemResult:
    label = f"skill:{name}"
    if label in conflicts:
        return ItemResult(label, required, True, False, CONFLICT, conflicts[label])
    skill_dir = target / ".agents" / "skills" / name
    if not skill_dir.is_dir():
        return ItemResult(label, required, False, False, FAIL, "not installed")
    errors = validate_skill(skill_dir)
    if errors:
        return ItemResult(label, required, True, True, FAIL, "; ".join(errors))
    for rel, data in iter_skill_files(kit_root, name):
        path = target / rel
        try:
            differs = not path.is_file() or path.read_bytes() != data
        except OSError as exc:
            return ItemResult(label, required, True, True, FAIL, f"cannot read {rel}: {exc}")
        if differs:
            return ItemResult(
                label, required, True, True, FAIL, f"files differ from the kit copy ({rel})"
            )
    return ItemResult(label, required, True, True, PASS)
