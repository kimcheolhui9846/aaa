import re

from kit.logs import mask

FORBIDDEN = [
    re.compile(r"git\s+push"),
    re.compile(r"curl[^\n|]*\|\s*(ba)?sh"),
    re.compile(r"\|\s*iex\b", re.IGNORECASE),
    re.compile(r"Invoke-Expression", re.IGNORECASE),
]
NETWORK_IMPORT = re.compile(r"^\s*(import|from)\s+(socket|urllib|http)\b", re.MULTILINE)
CODE_GLOBS = ["kit/*.py", "run_kit.py", "bootstrap.sh", "bootstrap.ps1"]


def test_mask_hides_tokens():
    text = (
        "sk-abcdefghijklmnopqrstuv ghp_ABCDEFGHIJKLMNOPQRSTUVWX12 "
        "API_KEY=hunter2 password: opensesame"
    )
    masked = mask(text)
    for secret in (
        "sk-abcdefghijklmnopqrstuv",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWX12",
        "hunter2",
        "opensesame",
    ):
        assert secret not in masked
    assert "API_KEY=***" in masked


def test_log_never_contains_environment_values(run_kit, workspace, monkeypatch):
    monkeypatch.setenv("KIT_TEST_SECRET", "ghp_" + "Z" * 30)
    run_kit()
    logs = list((workspace / ".kit" / "logs").glob("*.log"))
    assert logs
    for log in logs:
        assert "ZZZZZZZZZZ" not in log.read_text(encoding="utf-8")


def test_kit_code_has_no_push_or_pipe_to_shell(kit_root):
    files = [p for pattern in CODE_GLOBS for p in kit_root.glob(pattern)]
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            assert not pattern.search(text), f"{path.name}: {pattern.pattern}"


def test_kit_core_imports_no_network_modules(kit_root):
    for path in kit_root.glob("kit/*.py"):
        assert not NETWORK_IMPORT.search(path.read_text(encoding="utf-8")), path.name


def test_no_writes_outside_target(run_kit, workspace, tmp_path):
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    run_kit()
    assert list(sibling.iterdir()) == []
