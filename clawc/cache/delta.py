from __future__ import annotations

import difflib

NEAR_DUP_THRESHOLD = 8  # Hamming distance ≤ 8 bits out of 64


def _compute_simhash(text: str) -> int | None:
    try:
        from simhash import Simhash  # type: ignore[import]

        val = int(Simhash(text).value)
        # Convert unsigned 64-bit to signed so it fits SQLite INTEGER
        if val >= (1 << 63):
            val -= 1 << 64
        return val
    except ImportError:
        return None


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def find_near_dup(
    recent_entries: list[dict],
    content: str,
    content_hash: str,
) -> tuple[str, int, int] | None:
    """Return (base_hash, hamming_dist, base_simhash) or None."""
    new_sh = _compute_simhash(content)
    if new_sh is None:
        return None

    for entry in recent_entries:
        base_sh = entry.get("simhash")
        if base_sh is None:
            continue
        dist = hamming_distance(new_sh, base_sh)
        if 0 < dist <= NEAR_DUP_THRESHOLD:
            return entry["content_hash"], dist, new_sh

    return None


def make_patch(base_compressed: str, new_text: str) -> str:
    return "".join(
        difflib.unified_diff(
            base_compressed.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile="cached",
            tofile="current",
            lineterm="",
        )
    )


def compute_simhash(text: str) -> int | None:
    return _compute_simhash(text)
