"""Turn item results into READY/PARTIAL/BLOCKED, next actions and the printed report."""

from __future__ import annotations

from pathlib import Path

from .cli import Options
from .model import (
    CONFLICT,
    EXIT_BLOCKED,
    EXIT_PARTIAL,
    EXIT_READY,
    FAIL,
    PASS,
    ItemResult,
)
from .preflight import EnvReport

BAD = (FAIL, CONFLICT)


def overall_status(items: list[ItemResult], shell_fallback: bool = False) -> tuple[str, int]:
    if any(i.required and i.verified in BAD for i in items):
        return "BLOCKED", EXIT_BLOCKED
    if shell_fallback or any(i.verified in BAD for i in items):
        return "PARTIAL", EXIT_PARTIAL
    return "READY", EXIT_READY


def next_actions(items: list[ItemResult], target: Path, status: str) -> list[str]:
    actions = []
    for i in items:
        if i.verified == CONFLICT:
            actions.append(
                f"Resolve conflict in {i.name}: {i.detail}. Compare with the kit copy, then re-run."
            )
        elif i.verified == FAIL:
            actions.append(f"Fix {i.name}: {i.detail}. Then re-run.")
    if status != "BLOCKED":
        actions.append(f"Open Codex in {target} and run /skills to confirm the kit skills load.")
    return actions[:3]


def render(
    env: EnvReport,
    opts: Options,
    items: list[ItemResult],
    status: str,
    actions: list[str],
    network: str | None = None,
) -> str:
    skills = [i for i in items if i.name.startswith("skill:")]
    verified = sum(1 for i in skills if i.verified == PASS)
    agents = next((i for i in items if i.name == "AGENTS.md"), None)
    if agents is None:
        agents_label = "SKIPPED"
    else:
        agents_label = {PASS: "INSTALLED", CONFLICT: "CONFLICT"}.get(agents.verified, "FAILED")
    tools = ", ".join(
        f"{name} {'OK' if info.ok else 'missing'}" for name, info in env.tools.items()
    )
    mcp = "disabled (--no-mcp)" if opts.no_mcp else f"none in profile '{opts.profile}'"
    if network is None:
        network = "not used (--offline)" if opts.offline else "not used"

    lines = [
        f"Environment:  {env.os} {env.arch}, shell={env.shell}, python {env.python}",
        f"Tools:        {tools}",
        f"Target:       {opts.target}",
        f"Profile:      {opts.profile}",
        f"AGENTS.md:    {agents_label}",
        f"Skills:       {len(skills)} expected / {verified} verified",
        "Codex load:   UNVERIFIED (open Codex and run /skills)",
        f"MCP:          {mcp}",
        f"Network:      {network}",
    ]
    shown = items if opts.verbose else [i for i in items if i.verified in BAD]
    if shown:
        lines.append("Items:")
        for i in shown:
            kind = "required" if i.required else "optional"
            detail = f"  ({i.detail})" if i.detail else ""
            lines.append(f"  {i.verified:<10} {kind} {i.name}{detail}")
    lines.append(f"Status:       {status}")
    lines.append("Next action:")
    lines.extend(f"  - {a}" for a in actions)
    return "\n".join(lines) + "\n"
