import json

import pytest

from kit.model import FAIL, PASS, SKIPPED, UNVERIFIED
from kit.preflight import ToolInfo
from kit.webcheck import check_node_project, parse_version, satisfies

NODE = ToolInfo("node", "/fake/node", "v20.11.1")


@pytest.mark.parametrize(
    "spec, expected",
    [
        (">=18", True),
        (">=21", False),
        (">18.0.0", True),
        (">20", False),
        ("<21", True),
        ("<=20", True),
        ("<20", False),
        ("^20.1", True),
        ("^21", False),
        ("^0.1.0", False),
        ("~20.11.0", True),
        ("~20.10", False),
        ("20", True),
        ("20.x", True),
        ("18.x || 20.x", True),
        (">=16 <19", False),
        ("*", True),
        ("", True),
        ("1.0.0 - 2.0.0", None),
        ("lts/*", None),
    ],
)
def test_satisfies(spec, expected):
    assert satisfies((20, 11, 1), spec) is expected


def test_parse_version():
    assert parse_version("v20.11.1") == (20, 11, 1)
    assert parse_version("node") is None


def _pkg(workspace, data):
    (workspace / "package.json").write_text(json.dumps(data), encoding="utf-8")


def test_no_package_json_is_skipped(workspace):
    assert check_node_project(workspace, NODE).verified == SKIPPED


def test_matching_engines_pass_and_list_lockfile(workspace):
    _pkg(workspace, {"engines": {"node": ">=18"}})
    (workspace / "package-lock.json").write_text("{}", encoding="utf-8")
    item = check_node_project(workspace, NODE)
    assert item.verified == PASS and "package-lock.json" in item.detail


def test_mismatch_fails(workspace):
    _pkg(workspace, {"engines": {"node": ">=22"}})
    item = check_node_project(workspace, NODE)
    assert item.verified == FAIL and ">=22" in item.detail


def test_unparseable_range_is_unverified(workspace):
    _pkg(workspace, {"engines": {"node": "lts/*"}})
    assert check_node_project(workspace, NODE).verified == UNVERIFIED


def test_missing_node_fails(workspace):
    _pkg(workspace, {})
    assert check_node_project(workspace, ToolInfo("node")).verified == FAIL


def test_invalid_json_fails(workspace):
    (workspace / "package.json").write_text("{", encoding="utf-8")
    assert check_node_project(workspace, NODE).verified == FAIL


def test_web_profile_end_to_end(run_kit, workspace):
    _pkg(workspace, {"engines": {"node": ">=1"}})
    code, out = run_kit("--profile", "web", "--verbose")
    assert "node-project" in out
    assert code in (0, 1), out
