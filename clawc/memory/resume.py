from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawc.cache.store import CacheStore


def build_resume_context(store: CacheStore, session_id: str, cwd: str = "") -> str:
    stats = store.stats()
    total_saved = stats.get("tokens_saved", 0)
    total_compressions = stats.get("total_compressions", 0)

    if total_compressions == 0:
        return ""

    lines = [
        "[clawc] Active — tool output is compressed. §ref:HASH§ tokens reference cached content.",
        f"Session cache: {total_compressions} entries, "
        f"~{total_saved} tokens saved across sessions.",
        "Use `clawc expand <ref>` to restore any §ref§ to original content.",
    ]
    return "\n".join(lines)
