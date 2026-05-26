from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from clawc.cache.dedup import extract_hash_prefix, is_ref_token, make_ref_token, sha256_hex
from clawc.pipeline.stages.condense_logs import CondenseLogs
from clawc.pipeline.stages.strip_ansi import StripAnsi

_ANSI_FREE_RE = re.compile(r"\x1b\[")

stage_ansi = StripAnsi()
stage_condense = CondenseLogs()


@given(st.text())
@settings(max_examples=200)
def test_strip_ansi_idempotent(text: str) -> None:
    once = stage_ansi.apply(text)
    result = once if once is not None else text
    twice = stage_ansi.apply(result)
    assert twice is None or twice == result


@given(st.text())
@settings(max_examples=200)
def test_strip_ansi_no_escape_codes_remain(text: str) -> None:
    result = stage_ansi.apply(text)
    if result is not None:
        assert not _ANSI_FREE_RE.search(result)


def test_strip_ansi_removes_color_codes() -> None:
    colored = "\x1b[32mGreen text\x1b[0m normal"
    result = stage_ansi.apply(colored)
    assert result == "Green text normal"


def test_strip_ansi_passthrough_clean_text() -> None:
    clean = "just plain text"
    assert stage_ansi.apply(clean) is None


@given(st.text(min_size=1))
@settings(max_examples=200)
def test_condense_never_expands(text: str) -> None:
    result = stage_condense.apply(text)
    if result is not None:
        assert len(result.splitlines()) <= len(text.splitlines())


def test_condense_suppresses_long_repeats() -> None:
    text = "repeated line\n" * 20
    result = stage_condense.apply(text)
    assert result is not None
    assert len(result.splitlines()) < 20
    assert "suppressed" in result.lower()


def test_condense_preserves_short_repeats() -> None:
    text = "a\na\na\nb\nb\nb"
    result = stage_condense.apply(text)
    assert result is None or result.count("a") >= 3


@given(st.text())
@settings(max_examples=300)
def test_sha256_deterministic(text: str) -> None:
    assert sha256_hex(text) == sha256_hex(text)


@given(st.text(min_size=1))
@settings(max_examples=200)
def test_ref_token_roundtrip(content: str) -> None:
    h = sha256_hex(content)
    ref = make_ref_token(h)
    assert is_ref_token(ref)
    prefix = extract_hash_prefix(ref)
    assert h.startswith(prefix)


def test_different_content_different_hash() -> None:
    assert sha256_hex("hello") != sha256_hex("world")
