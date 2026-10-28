"""Local-only run logs with secrets masked. Environment variable values are never logged."""

from __future__ import annotations

import re
from pathlib import Path

from .fsops import safe_path

_PATTERNS = [
    (re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[=:]\s*\S+"), r"\1=***"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "***"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "***"),
]


def mask(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def write_log(target: Path, text: str, stamp: str) -> Path:
    path = safe_path(target, f".kit/logs/{stamp}.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(mask(text).encode("utf-8"))
    return path
