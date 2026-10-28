"""Profile loading. A profile may extend another; list fields merge base-first."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .model import UsageError

LIST_KEYS = ("skills", "required_skills", "tools", "mcp")


@dataclass
class Profile:
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    mcp: list[str] = field(default_factory=list)


def available_profiles(kit_root: Path) -> list[str]:
    return sorted(path.stem for path in (kit_root / "profiles").glob("*.json"))


def _read(kit_root: Path, name: str) -> dict:
    path = kit_root / "profiles" / f"{name}.json"
    if not path.is_file():
        available = ", ".join(available_profiles(kit_root))
        raise UsageError(f"unknown profile '{name}' (available: {available})")
    return json.loads(path.read_text(encoding="utf-8"))


def load_profile(kit_root: Path, name: str) -> Profile:
    chain: list[dict] = []
    seen: set[str] = set()
    current: str | None = name
    while current:
        if current in seen:
            raise UsageError(f"profile inheritance cycle at '{current}'")
        seen.add(current)
        data = _read(kit_root, current)
        chain.append(data)
        current = data.get("extends")

    merged: dict[str, list] = {key: [] for key in LIST_KEYS}
    for data in reversed(chain):
        for key in LIST_KEYS:
            for item in data.get(key, []):
                if item not in merged[key]:
                    merged[key].append(item)
    return Profile(name=name, description=chain[0].get("description", ""), **merged)
