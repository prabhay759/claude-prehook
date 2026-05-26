from __future__ import annotations

from pathlib import Path

from clawc.cache.dedup import sha256_hex
from clawc.cache.store import CacheStore


def test_store_and_lookup(tmp_path: Path) -> None:
    store = CacheStore.open(tmp_path / "test.db")
    content = "hello world"
    h = sha256_hex(content)
    ref = store.store(h, content, "compressed hello", "Bash")
    assert ref.startswith("§ref:")
    entry = store.lookup(h)
    assert entry is not None
    assert entry["compressed"] == "compressed hello"
    assert entry["ref_token"] == ref


def test_cache_hit_increments_count(tmp_path: Path) -> None:
    store = CacheStore.open(tmp_path / "test.db")
    h = sha256_hex("repeated content")
    store.store(h, "repeated content", "compressed", "Bash")
    store.record_hit(h)
    store.record_hit(h)
    entry = store.lookup(h)
    assert entry["hit_count"] == 2


def test_stats_returns_summary(tmp_path: Path) -> None:
    store = CacheStore.open(tmp_path / "test.db")
    store.ensure_session("s1")
    store.record_compression("s1", "Bash", None, 100, 70, ["strip_ansi"])
    store.record_compression("s1", "Bash", None, 200, 50, ["condense_logs"], was_cache_hit=True)
    stats = store.stats()
    assert stats["total_compressions"] == 2
    assert stats["tokens_saved"] == 180
    assert stats["cache_hits"] == 1


def test_lookup_by_ref(tmp_path: Path) -> None:
    store = CacheStore.open(tmp_path / "test.db")
    h = sha256_hex("abc")
    ref = store.store(h, "abc", "compressed abc", "Read")
    entry = store.lookup_by_ref(ref)
    assert entry is not None
    assert entry["compressed"] == "compressed abc"
