from __future__ import annotations

import pytest

from clawc.cache.dedup import (
    REF_PREFIX,
    REF_SUFFIX,
    extract_hash_prefix,
    is_ref_token,
    make_ref_token,
    sha256_hex,
)


def test_sha256_returns_64_hex_chars() -> None:
    h = sha256_hex("hello world")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_make_ref_token_format() -> None:
    h = sha256_hex("test content")
    ref = make_ref_token(h)
    assert ref.startswith(REF_PREFIX)
    assert ref.endswith(REF_SUFFIX)
    assert len(ref) == len(REF_PREFIX) + 8 + len(REF_SUFFIX)


def test_is_ref_token() -> None:
    h = sha256_hex("abc")
    ref = make_ref_token(h)
    assert is_ref_token(ref)
    assert not is_ref_token("plain text")
    assert not is_ref_token("§ref:abc")  # missing suffix
    assert not is_ref_token("ref:abc§")  # missing prefix


def test_extract_hash_prefix() -> None:
    h = sha256_hex("content")
    ref = make_ref_token(h)
    prefix = extract_hash_prefix(ref)
    assert h.startswith(prefix)
    assert len(prefix) == 8
