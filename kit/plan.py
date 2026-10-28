"""Decide, without writing anything, what should happen to each kit file in the target."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import agentsmd, mcpconfig
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


def _plan_block(
    target: Path, rel: str, owner: str, body: str, state: State, begin: str, end: str
) -> FileChange:
    try:
        path = safe_path(target, rel)
        if path.exists() and not path.is_file():
            return FileChange(
                rel, owner, Outcome.CONFLICT, detail="exists but is not a regular file"
            )
        existing = path.read_bytes().decode("utf-8") if path.is_file() else None
    except PathEscapeError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=str(exc))
    except UnicodeDecodeError:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=f"existing {rel} is not UTF-8")
    except OSError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=f"cannot read {rel}: {exc}")
    text, outcome, detail = agentsmd.merge(existing, body, state.files.get(rel), begin, end)
    if outcome == Outcome.CONFLICT:
        return FileChange(rel, owner, outcome, detail=detail)
    data = text.encode("utf-8") if text is not None else None
    return FileChange(rel, owner, outcome, data, sha256(body.strip().encode("utf-8")), detail)


def plan_agents_md(target: Path, kit_root: Path, state: State) -> FileChange:
    body = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    return _plan_block(target, "AGENTS.md", "AGENTS.md", body, state, agentsmd.BEGIN, agentsmd.END)


def plan_mcp_config(target: Path, kit_root: Path, names: list[str], state: State) -> FileChange:
    body = mcpconfig.render_servers(mcpconfig.select_servers(kit_root, names))
    change = _plan_block(
        target, mcpconfig.CONFIG_REL, "mcp-config", body, state, mcpconfig.BEGIN, mcpconfig.END
    )
    if change.data is not None:
        problem = mcpconfig.check_merged(change.data.decode("utf-8"), names)
        if problem:
            return FileChange(change.rel, change.owner, Outcome.CONFLICT, detail=problem)
    return change


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
    try:
        current = sha256(path.read_bytes())
    except OSError as exc:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=f"cannot read file: {exc}")
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


def plan_changes(
    target: Path, kit_root: Path, profile: Profile, state: State, include_mcp: bool = True
) -> list[FileChange]:
    changes = [plan_agents_md(target, kit_root, state)]
    for name in profile.skills:
        for rel, data in iter_skill_files(kit_root, name):
            changes.append(plan_file(target, rel, f"skill:{name}", data, state))
    if include_mcp and profile.mcp:
        changes.append(plan_mcp_config(target, kit_root, profile.mcp, state))
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
