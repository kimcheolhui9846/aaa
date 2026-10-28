"""Decide, without writing anything, what should happen to each kit file in the target."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import agentsmd
from .fsops import PathEscapeError, State, safe_path, sha256
from .model import Outcome
from .profiles import Profile


@dataclass
class FileChange:
    rel: str
    owner: str
    outcome: str
    data: bytes | None = None
    record: str | None = None
    detail: str = ""


def iter_skill_files(kit_root: Path, name: str) -> list[tuple[str, bytes]]:
    src = kit_root / ".agents" / "skills" / name
    return [
        (f".agents/skills/{name}/{path.relative_to(src).as_posix()}", path.read_bytes())
        for path in sorted(src.rglob("*"))
        if path.is_file()
    ]


def plan_agents_md(target: Path, kit_root: Path, state: State) -> FileChange:
    rel = owner = "AGENTS.md"
    body = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    try:
        path = safe_path(target, rel)
        existing = path.read_bytes().decode("utf-8") if path.is_file() else None
    except PathEscapeError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=str(exc))
    except UnicodeDecodeError:
        return FileChange(rel, owner, Outcome.CONFLICT, detail="existing AGENTS.md is not UTF-8")
    text, outcome, detail = agentsmd.merge(existing, body, state.files.get(rel))
    if outcome == Outcome.CONFLICT:
        return FileChange(rel, owner, outcome, detail=detail)
    data = text.encode("utf-8") if text is not None else None
    return FileChange(rel, owner, outcome, data, sha256(body.strip().encode("utf-8")), detail)


def plan_file(target: Path, rel: str, owner: str, data: bytes, state: State) -> FileChange:
    try:
        path = safe_path(target, rel)
    except PathEscapeError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=str(exc))
    new_hash = sha256(data)
    if not path.exists():
        return FileChange(rel, owner, Outcome.CREATE, data, new_hash)
    if not path.is_file():
        return FileChange(rel, owner, Outcome.CONFLICT, detail="exists but is not a regular file")
    current = sha256(path.read_bytes())
    if current == new_hash:
        return FileChange(rel, owner, Outcome.UNCHANGED, None, new_hash)
    if state.files.get(rel) == current:
        return FileChange(rel, owner, Outcome.UPDATE, data, new_hash)
    return FileChange(
        rel,
        owner,
        Outcome.CONFLICT,
        detail="differs from the kit copy and was not written by the kit",
    )


def plan_changes(target: Path, kit_root: Path, profile: Profile, state: State) -> list[FileChange]:
    changes = [plan_agents_md(target, kit_root, state)]
    for name in profile.skills:
        for rel, data in iter_skill_files(kit_root, name):
            changes.append(plan_file(target, rel, f"skill:{name}", data, state))
    return changes


def format_plan(changes: list[FileChange], verbose: bool = False) -> str:
    counts = dict.fromkeys(Outcome.ALL, 0)
    lines = []
    for change in changes:
        counts[change.outcome] += 1
        if change.outcome == Outcome.UNCHANGED and not verbose:
            continue
        suffix = f"  ({change.detail})" if change.detail else ""
        lines.append(f"  {change.outcome.upper():<9} {change.rel}{suffix}")
    lines.append("Summary:      " + ", ".join(f"{counts[o]} {o}" for o in Outcome.ALL))
    return "\n".join(lines)
