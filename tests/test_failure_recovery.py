import os


def test_interrupted_run_recovers_on_rerun(run_kit, workspace, monkeypatch):
    real_replace = os.replace
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("simulated disk error")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    code, out = run_kit()
    assert code == 2, out
    assert "error: write failed: simulated disk error" in out

    monkeypatch.setattr(os, "replace", real_replace)
    code, out = run_kit()
    assert code == 0, out
    assert not list(workspace.rglob("*.kit-tmp"))
