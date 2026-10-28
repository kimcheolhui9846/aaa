from conftest import tree_digest


def test_second_run_changes_nothing(run_kit, workspace):
    assert run_kit()[0] == 0
    first = tree_digest(workspace)
    code, out = run_kit()
    assert code == 0, out
    assert tree_digest(workspace) == first


def test_dry_run_writes_nothing(run_kit, workspace):
    code, out = run_kit("--dry-run")
    assert code == 0, out
    assert "CREATE" in out and "DRY RUN: nothing was written." in out
    assert list(workspace.iterdir()) == []


def test_dry_run_after_install_plans_nothing(run_kit):
    run_kit()
    code, out = run_kit("--dry-run")
    assert code == 0
    assert "0 create, 0 update, 0 append, 0 conflict" in out


def test_lost_state_is_adopted(run_kit, workspace):
    run_kit()
    state = workspace / ".kit" / "state.json"
    before = state.read_bytes()
    state.unlink()
    code, out = run_kit()
    assert code == 0, out
    assert state.read_bytes() == before


def test_verify_only_writes_only_logs(run_kit, workspace):
    code, out = run_kit("--verify-only")
    assert code == 2, out
    written = [p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()]
    assert written and all(rel.startswith(".kit/logs/") for rel in written)
