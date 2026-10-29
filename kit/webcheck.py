"""web profile: read package.json and check node against engines.node. Installs nothing."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .model import FAIL, PASS, SKIPPED, UNVERIFIED, ItemResult
from .preflight import ToolInfo

LABEL = "node-project"
LOCKFILES = (
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
)
_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
_COMPARATOR = re.compile(r"^(>=|<=|>|<|=|\^|~)?v?(\d+|x|\*)(?:\.(\d+|x|\*))?(?:\.(\d+|x|\*))?$")


def parse_version(text: str | None) -> tuple[int, int, int] | None:
    match = _VERSION.search(text or "")
    if not match:
        return None
    major, minor, patch = (int(g) for g in match.groups())
    return major, minor, patch


def _upper_caret(nums: list[int]) -> tuple[int, ...]:
    index = next((i for i, n in enumerate(nums) if n > 0), len(nums) - 1)
    bumped = nums[:index] + [nums[index] + 1]
    return tuple(bumped + [0] * (3 - len(bumped)))


def _match(version: tuple[int, int, int], comparator: str) -> bool | None:
    match = _COMPARATOR.match(comparator)
    if not match:
        return None
    op, *raw = match.groups()
    nums: list[int] = []
    for part in raw:
        if part is None or part in ("x", "*"):
            break
        nums.append(int(part))
    if not nums:
        return True
    prefix, wanted = version[: len(nums)], tuple(nums)
    base = tuple(nums + [0] * (3 - len(nums)))
    if op in (None, "="):
        return prefix == wanted
    if op == ">=":
        return prefix >= wanted
    if op == ">":
        return prefix > wanted
    if op == "<=":
        return prefix <= wanted
    if op == "<":
        return prefix < wanted
    if op == "^":
        return base <= version < _upper_caret(nums)
    upper = (nums[0], nums[1] + 1, 0) if len(nums) >= 2 else (nums[0] + 1, 0, 0)
    return base <= version < upper


def satisfies(version: tuple[int, int, int], spec: str) -> bool | None:
    spec = spec.strip()
    if spec in ("", "*", "x"):
        return True
    results = []
    for alternative in spec.split("||"):
        parts = alternative.split()
        if not parts:
            return None
        verdicts = [_match(version, part) for part in parts]
        if any(v is None for v in verdicts):
            return None
        results.append(all(verdicts))
    return any(results)


def check_node_project(target: Path, node: ToolInfo | None) -> ItemResult:
    path = target / "package.json"
    if not path.is_file():
        return ItemResult(LABEL, False, False, False, SKIPPED, "no package.json in target")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return ItemResult(LABEL, False, True, False, FAIL, f"package.json is not valid JSON: {exc}")
    locks = [name for name in LOCKFILES if (target / name).is_file()]
    lock_text = f"lockfiles: {', '.join(locks)}" if locks else "no lockfile"
    if node is None or not node.ok:
        return ItemResult(LABEL, False, True, False, FAIL, f"node not found; {lock_text}")
    engines = data.get("engines") if isinstance(data, dict) else None
    spec = engines.get("node") if isinstance(engines, dict) else None
    if not isinstance(spec, str):
        return ItemResult(LABEL, False, True, True, PASS, f"node {node.version}; {lock_text}")
    version = parse_version(node.version)
    verdict = satisfies(version, spec) if version else None
    if verdict is None:
        detail = f"cannot evaluate engines.node '{spec}' against {node.version}; {lock_text}"
        return ItemResult(LABEL, False, True, True, UNVERIFIED, detail)
    if not verdict:
        detail = f"node {node.version} does not satisfy engines.node '{spec}'; {lock_text}"
        return ItemResult(LABEL, False, True, True, FAIL, detail)
    return ItemResult(
        LABEL, False, True, True, PASS, f"node {node.version} satisfies '{spec}'; {lock_text}"
    )
