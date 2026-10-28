import pytest

from kit.cli import parse_args
from kit.model import TargetError, UsageError

PROFILES = ["core"]


def test_defaults(workspace):
    opts = parse_args([], workspace, PROFILES)
    assert opts.profile == "core"
    assert opts.target == workspace.resolve()
    assert not (opts.dry_run or opts.offline or opts.verify_only or opts.no_mcp or opts.verbose)


def test_flags(workspace):
    opts = parse_args(["--dry-run", "--offline", "--no-mcp", "--verbose"], workspace, PROFILES)
    assert opts.dry_run and opts.offline and opts.no_mcp and opts.verbose


def test_relative_target_resolves_against_cwd(tmp_path, workspace):
    opts = parse_args(["--target", "ws"], tmp_path, PROFILES)
    assert opts.target == workspace.resolve()


def test_unknown_flag(workspace):
    with pytest.raises(UsageError):
        parse_args(["--bogus"], workspace, PROFILES)


def test_unknown_profile(workspace):
    with pytest.raises(UsageError):
        parse_args(["--profile", "gpu"], workspace, PROFILES)


def test_missing_target(tmp_path):
    with pytest.raises(TargetError):
        parse_args(["--target", str(tmp_path / "missing")], tmp_path, PROFILES)


def test_target_is_a_file(tmp_path):
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    with pytest.raises(TargetError):
        parse_args(["--target", "f.txt"], tmp_path, PROFILES)


def test_dry_run_and_verify_only_conflict(workspace):
    with pytest.raises(UsageError, match="cannot be combined"):
        parse_args(["--dry-run", "--verify-only"], workspace, PROFILES)


def test_help_exits_zero(workspace, capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(["--help"], workspace, PROFILES)
    assert exc.value.code == 0
    assert "exit codes" in capsys.readouterr().out
