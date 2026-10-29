"""Shared result types, verdicts and exit codes."""

from __future__ import annotations

from dataclasses import dataclass

EXIT_READY = 0
EXIT_PARTIAL = 1
EXIT_BLOCKED = 2
EXIT_USAGE = 64
EXIT_TARGET = 65

PASS = "PASS"
FAIL = "FAIL"
UNVERIFIED = "UNVERIFIED"
SKIPPED = "SKIPPED"
CONFLICT = "CONFLICT"


class Outcome:
    """What the planner decided to do with one file."""

    CREATE = "create"
    UPDATE = "update"
    APPEND = "append"
    CONFLICT = "conflict"
    UNCHANGED = "unchanged"
    ALL = (CREATE, UPDATE, APPEND, CONFLICT, UNCHANGED)


class UsageError(Exception):
    """Invalid command-line arguments (exit 64)."""


class TargetError(Exception):
    """Target workspace is missing or not a directory (exit 65)."""


@dataclass
class ItemResult:
    name: str
    required: bool
    installed: bool
    registered: bool
    verified: str
    detail: str = ""
