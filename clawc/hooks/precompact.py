from __future__ import annotations

from ._protocol import EXIT_CONTINUE, HookInput, HookOutput


def handle(inp: HookInput) -> None:
    from clawc.cache.store import CacheStore

    store = CacheStore.open()
    stats = store.stats(inp.session_id or None)
    tokens_saved = stats.get("tokens_saved", 0)

    if tokens_saved > 0:
        msg = (
            f"[clawc] Pre-compact snapshot: {stats.get('total_compressions', 0)} compressions, "
            f"{tokens_saved} tokens saved ({stats.get('reduction_pct', 0):.1f}% reduction). "
            "§ref:HASH§ tokens in context may need re-expansion after compaction."
        )
        HookOutput(
            hook_specific_output={
                "hookEventName": "PreCompact",
                "additionalContext": msg,
            }
        ).emit(EXIT_CONTINUE)
    else:
        HookOutput().emit(EXIT_CONTINUE)
