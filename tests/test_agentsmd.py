import pytest

from kit.agentsmd import BEGIN, END, MarkerError, extract_block, merge, render_block
from kit.fsops import sha256

BODY = "# Policy\n- rule one\n"


def test_render_block_wraps_stripped_body():
    assert render_block(BODY) == f"{BEGIN}\n# Policy\n- rule one\n{END}\n"


def test_merge_creates_when_missing():
    text, outcome, _ = merge(None, BODY, None)
    assert outcome == "create" and text == render_block(BODY)


def test_merge_creates_when_blank():
    text, outcome, _ = merge(" \n", BODY, None)
    assert outcome == "create" and text == render_block(BODY)


def test_merge_appends_and_preserves_existing_bytes():
    existing = "# Team rules\r\nKeep CRLF.\r\n"
    text, outcome, _ = merge(existing, BODY, None)
    assert outcome == "append"
    assert text == existing + "\n" + render_block(BODY)


def test_merge_appends_newline_when_missing():
    text, outcome, _ = merge("no newline", BODY, None)
    assert outcome == "append"
    assert text == "no newline\n\n" + render_block(BODY)


def test_merge_unchanged_when_block_matches():
    text, outcome, _ = merge("intro\n\n" + render_block(BODY), BODY, None)
    assert outcome == "unchanged" and text is None


def test_merge_updates_block_written_by_kit():
    old = "# Policy\n- old rule\n"
    existing = "intro\n\n" + render_block(old) + "outro\n"
    text, outcome, _ = merge(existing, BODY, sha256(old.strip().encode("utf-8")))
    assert outcome == "update"
    assert text == "intro\n\n" + render_block(BODY) + "outro\n"


def test_merge_updates_block_with_crlf_after_end_marker():
    old = "old"
    existing = f"{BEGIN}\r\nold\r\n{END}\r\ntail\r\n"
    text, outcome, _ = merge(existing, BODY, sha256(old.encode("utf-8")))
    assert outcome == "update"
    assert text == render_block(BODY) + "tail\r\n"


def test_merge_conflict_when_user_edited_block():
    existing = render_block("# Policy\n- user changed this\n")
    text, outcome, detail = merge(existing, BODY, sha256(b"something else"))
    assert outcome == "conflict" and text is None and "edited" in detail


def test_merge_conflict_when_block_has_no_record():
    _, outcome, _ = merge(render_block("different"), BODY, None)
    assert outcome == "conflict"


@pytest.mark.parametrize(
    "text",
    [
        f"{BEGIN}\nx\n",
        f"x\n{END}\n",
        f"{END}\n{BEGIN}\n",
        f"{BEGIN}\n{BEGIN}\n{END}\n",
    ],
)
def test_malformed_markers(text):
    with pytest.raises(MarkerError):
        extract_block(text)
    assert merge(text, BODY, None)[1] == "conflict"


def test_extract_block_none_without_markers():
    assert extract_block("plain\n") is None


def test_merge_unchanged_when_block_has_crlf():
    existing = "intro\r\n" + render_block(BODY).replace("\n", "\r\n")
    text, outcome, _ = merge(existing, BODY, None)
    assert outcome == "unchanged" and text is None


def test_merge_updates_crlf_block_written_by_kit():
    old = "# Policy\n- old rule\n"
    existing = render_block(old).replace("\n", "\r\n") + "tail\r\n"
    text, outcome, _ = merge(existing, BODY, sha256(old.strip().encode("utf-8")))
    assert outcome == "update"
    assert text == render_block(BODY) + "tail\r\n"


def test_extract_block_normalizes_crlf_interior():
    assert extract_block(f"{BEGIN}\r\na\r\nb\r\n{END}\r\n")[2] == "a\nb"
