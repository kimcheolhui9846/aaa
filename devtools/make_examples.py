"""Regenerate docs/examples/*.log from real kit runs in temporary workspaces. No network."""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kit.app import run  # noqa: E402

OUT = ROOT / "docs" / "examples"


def _run(target: Path, *argv: str) -> str:
    out = io.StringIO()
    code = run(["--target", str(target), *argv], cwd=target, out=out)
    text = out.getvalue()
    for path in {str(target), str(target.resolve())}:
        text = text.replace(path, "<target>")
    text = text.replace(str(Path.home()), "<home>")
    return f"$ bootstrap {' '.join(argv)}\n{text}(exit {code})\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for name in ("install", "rerun", "failure", "offline", "conflict"):
            (base / name).mkdir()
        logs = {
            "install": _run(base / "install"),
        }
        _run(base / "rerun")
        logs["rerun"] = _run(base / "rerun", "--verbose")
        (base / "failure" / "AGENTS.md").write_text(
            "<!-- hackathon-kit:begin -->\n<!-- hackathon-kit:begin -->\n", encoding="utf-8"
        )
        logs["failure"] = _run(base / "failure")
        logs["offline"] = _run(base / "offline", "--profile", "python", "--offline")
        _run(base / "conflict")
        skill = base / "conflict" / ".agents" / "skills" / "benchmark" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nmy note\n", encoding="utf-8")
        logs["conflict"] = _run(base / "conflict")
    for name, text in logs.items():
        (OUT / f"{name}.log").write_bytes(text.encode("utf-8"))
        print(f"wrote docs/examples/{name}.log")


if __name__ == "__main__":
    main()
