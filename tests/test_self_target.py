from kit.app import SELF_TARGET_MSG


def test_kit_folder_as_target_is_refused(run_kit, kit_root, capsys):
    before = (kit_root / "AGENTS.md").read_bytes()
    for _ in range(2):
        code, _ = run_kit("--target", str(kit_root))
        assert code == 65
    assert SELF_TARGET_MSG in capsys.readouterr().err
    assert (kit_root / "AGENTS.md").read_bytes() == before


def test_kit_folder_as_cwd_is_refused(run_kit, kit_root):
    before = (kit_root / "AGENTS.md").read_bytes()
    code, _ = run_kit(cwd=kit_root)
    assert code == 65
    assert (kit_root / "AGENTS.md").read_bytes() == before


def test_empty_target_exits_64(run_kit):
    code, _ = run_kit("--target", "")
    assert code == 64
