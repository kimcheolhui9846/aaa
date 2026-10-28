from kit import model


def test_exit_codes():
    codes = [
        model.EXIT_READY,
        model.EXIT_PARTIAL,
        model.EXIT_BLOCKED,
        model.EXIT_USAGE,
        model.EXIT_TARGET,
    ]
    assert codes == [0, 1, 2, 64, 65]


def test_outcomes_are_ordered():
    assert model.Outcome.ALL == ("create", "update", "append", "conflict", "unchanged")


def test_item_result_defaults():
    item = model.ItemResult("AGENTS.md", True, True, True, model.PASS)
    assert item.detail == ""
