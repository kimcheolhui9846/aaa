"""Entry used by bootstrap.sh/.ps1 (`python -I run_kit.py ...`); avoids PYTHONPATH quirks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit.app import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
